#!/usr/bin/env python3
"""verify_quote_performance.py 동작 확인.

실행: python3 -m unittest artifacts/scripts/test_verify_quote_performance.py -v

모든 입력은 손으로 기대값을 계산할 수 있는 가상 수치이며 특정 고객의 수치가 아니다.
기본 입력: 수수료 10%, VAT 10%, 판매가 30,000원, 구매당 1개, 월 청구 예산 1,210,000원.
- 월 순매체비 1,000,000 → 수수료 100,000, 공급가액 1,100,000, VAT 110,000, 청구 1,210,000
- M1 A: 600,000÷500=1,200회, ×2%=24건, 720,000원, CPA 25,000, ROAS 120.0
- M1 B: 400,000÷400=1,000회, ×1.5%=15건, 450,000원, CPA 26,666.67→26,667, ROAS 112.5
- M1 합계: 2,200회, 39건, 1,170,000원, CPA 25,641.03→25,641, ROAS 117.0
- M2 A: 700,000÷500=1,400회, ×3%=42건, 1,260,000원, CPA 16,666.67→16,667, ROAS 180.0
- M2 B: 300,000÷300=1,000회, ×2%=20건, 600,000원, CPA 15,000, ROAS 200.0
- M2 합계: 2,400회, 62건, 1,860,000원, CPA 16,129.03→16,129, ROAS 186.0
- 누적: 2,000,000원, 4,600회, 101건, 3,030,000원, CPA 19,801.98→19,802, ROAS 151.5
  (월별 CPA 단순 평균 20,885와 다름)
"""

import copy
import json
import os
import subprocess
import sys
import tempfile
import unittest
from decimal import Decimal

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import verify_quote_performance as v  # noqa: E402

SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "verify_quote_performance.py")


def quote(net, fee, supply, vat, billing):
    return {"net_media": net, "fee": fee, "supply": supply, "vat": vat, "billing": billing}


def perf(net, clicks, conv, rev, cpa, roas, media=None):
    row = {"net_media": net, "clicks": clicks, "conversions": conv, "revenue": rev,
           "cpa": cpa, "roas_percent": roas}
    if media:
        row["media"] = media
    return row


def base_input():
    return {
        "label": "테스트 정상값",
        "conditions": {
            "fee_rate_percent": "10",
            "vat_rate_percent": "10",
            "unit_price": "30,000",
            "units_per_purchase": 1,
            "contract_total_budget": "2,420,000",
            "months": [
                {"month": "M1", "billing_budget": "1,210,000", "assumptions": [
                    {"media": "A", "cpc": "500", "cvr_percent": "2"},
                    {"media": "B", "cpc": "400", "cvr_percent": "1.5"}]},
                {"month": "M2", "billing_budget": "1,210,000", "assumptions": [
                    {"media": "A", "cpc": "500", "cvr_percent": "3"},
                    {"media": "B", "cpc": "300", "cvr_percent": "2"}]},
            ],
        },
        "document": {
            "display": {"clicks_decimals": 2, "revenue_decimals": 0, "ratio_percent_decimals": 1},
            "months": [
                {"month": "M1",
                 "quote": quote("1,000,000", "100,000", "1,100,000", "110,000", "1,210,000"),
                 "allocation": [{"name": "A", "net_media": "600,000", "ratio_percent": "60.0"},
                                {"name": "B", "net_media": "400,000", "ratio_percent": "40.0"}],
                 "media": [perf("600,000", "1,200", "24", "720,000", "25,000", "120.0", "A"),
                           perf("400,000", "1,000", "15", "450,000", "26,667", "112.5", "B")],
                 "total": perf("1,000,000", "2,200", "39", "1,170,000", "25,641", "117.0")},
                {"month": "M2",
                 "quote": quote("1,000,000", "100,000", "1,100,000", "110,000", "1,210,000"),
                 "allocation": [{"name": "A", "net_media": "700,000", "ratio_percent": "70.0"},
                                {"name": "B", "net_media": "300,000", "ratio_percent": "30.0"}],
                 "media": [perf("700,000", "1,400", "42", "1,260,000", "16,667", "180.0", "A"),
                           perf("300,000", "1,000", "20", "600,000", "15,000", "200.0", "B")],
                 "total": perf("1,000,000", "2,400", "62", "1,860,000", "16,129", "186.0")},
            ],
            "contract_quote": quote("2,000,000", "200,000", "2,200,000", "220,000", "2,420,000"),
            "cumulative": perf("2,000,000", "4,600", "101", "3,030,000", "19,802", "151.5"),
        },
    }


def parse(data):
    """JSON 왕복으로 load_input과 같은 Decimal 입력을 만든다."""
    text = json.dumps(data, ensure_ascii=False)
    return json.loads(text, parse_float=Decimal, parse_int=Decimal)


def find(report, section, item):
    hits = [c for c in report.checks if c["section"] == section and c["item"] == item]
    if len(hits) != 1:
        raise AssertionError(f"{section} / {item} 검사가 {len(hits)}건")
    return hits[0]


class NormalValues(unittest.TestCase):
    def test_all_checks_match(self):
        report = v.run(parse(base_input()))
        bad = [c for c in report.checks if c["status"] != v.MATCH]
        self.assertEqual(bad, [])
        self.assertTrue(report.passed())

    def test_budget_solution(self):
        self.assertEqual(v.solve_net_media(Decimal(1210000), Decimal("0.10"), Decimal("0.10")),
                         [Decimal(1000000)])
        report = v.run(parse(base_input()))
        self.assertEqual(find(report, "M1 견적", "순매체비(예산 역산)")["computed"], "1,000,000")

    def test_contract_total_is_sum_of_monthly_billing(self):
        report = v.run(parse(base_input()))
        c = find(report, "계약 합계", "청구 총액")
        self.assertEqual((c["status"], c["computed"]), (v.MATCH, "2,420,000"))


class Mismatch(unittest.TestCase):
    def test_fee_off_by_one(self):
        data = base_input()
        data["document"]["months"][0]["quote"]["fee"] = "100,001"
        report = v.run(parse(data))
        c = find(report, "M1 견적", "수수료")
        self.assertEqual((c["status"], c["document"], c["computed"]), (v.MISMATCH, "100,001", "100,000"))
        self.assertFalse(report.passed())

    def test_cpa_off(self):
        data = base_input()
        data["document"]["months"][0]["media"][1]["cpa"] = "26,666"
        report = v.run(parse(data))
        c = find(report, "M1 성과 · B", "CPA")
        self.assertEqual((c["status"], c["computed"]), (v.MISMATCH, "26,667"))

    def test_allocation_sum_differs_from_net_media(self):
        data = base_input()
        data["document"]["months"][0]["allocation"][1]["net_media"] = "399,999"
        report = v.run(parse(data))
        self.assertEqual(find(report, "M1 배분", "매체 금액 합계")["status"], v.MISMATCH)

    def test_billing_not_equal_to_budget(self):
        data = base_input()
        data["conditions"]["months"][0]["billing_budget"] = "1,210,001"
        report = v.run(parse(data))
        self.assertEqual(find(report, "M1 견적", "청구 총액과 월 예산")["status"], v.MISMATCH)


class Rounding(unittest.TestCase):
    rate = Decimal("0.10")

    def test_fee_half_up(self):
        q = v.quote_from_net(Decimal(1000005), self.rate, self.rate)
        self.assertEqual(q["fee"][1], Decimal(100001))  # 100,000.5 → 100,001
        self.assertEqual(q["vat"][1], Decimal(110001))  # 110,000.6 → 110,001
        self.assertEqual(q["billing"][1], Decimal(1210007))

    def test_vat_half_up(self):
        q = v.quote_from_net(Decimal(1000023), self.rate, self.rate)
        self.assertEqual(q["supply"][1], Decimal(1100025))
        self.assertEqual(q["vat"][1], Decimal(110003))  # 110,002.5 → 110,003 (짝수 반올림이면 110,002)

    def test_budget_solution_uses_half_up(self):
        # 짝수 반올림이면 1,000,005의 청구액은 1,210,005가 되어 해가 달라진다.
        self.assertEqual(v.solve_net_media(Decimal(1210007), self.rate, self.rate), [Decimal(1000005)])

    def test_conversion_display_half_up(self):
        p = v.performance(Decimal(100500), Decimal(1000), Decimal("0.01"), Decimal(30000), Decimal(1))
        self.assertEqual(p["conversions"], Decimal("1.005"))
        self.assertEqual(v.round_to(p["conversions"], 2), Decimal("1.01"))

    def test_no_intermediate_rounding(self):
        # 100,000÷300=333.33…회, ×1%=3.333…건. 반올림 전 값으로 매출 100,000·CPA 30,000·ROAS 100.0.
        # 전환을 3.33으로 먼저 반올림하면 매출 99,900·CPA 30,030이 되어 틀린다.
        p = v.performance(Decimal(100000), Decimal(300), Decimal("0.01"), Decimal(30000), Decimal(1))
        p.update(v.ratios(p))
        self.assertEqual(v.round_to(p["conversions"], 2), Decimal("3.33"))
        self.assertEqual(v.round_to(p["revenue"], 0), Decimal(100000))
        self.assertEqual(v.round_to(p["cpa"], 0), Decimal(30000))
        self.assertEqual(v.round_to(p["roas_percent"], 1), Decimal("100.0"))

    def test_ratio_display(self):
        data = base_input()
        data["document"]["months"][0]["allocation"][0]["ratio_percent"] = "60"
        report = v.run(parse(data))
        self.assertEqual(find(report, "M1 배분", "A 비율(%)")["status"], v.MATCH)
        data["document"]["months"][0]["allocation"][0]["ratio_percent"] = "60.1"
        report = v.run(parse(data))
        self.assertEqual(find(report, "M1 배분", "A 비율(%)")["status"], v.MISMATCH)


class Cumulative(unittest.TestCase):
    def test_cumulative_uses_summed_values(self):
        report = v.run(parse(base_input()))
        self.assertEqual(find(report, "계약 누적 성과", "CPA")["computed"], "19,802")
        self.assertEqual(find(report, "계약 누적 성과", "ROAS(%)")["computed"], "151.5")
        self.assertEqual(find(report, "M1 성과 · 월 합계", "CPA")["computed"], "25,641")

    def test_simple_average_is_rejected(self):
        data = base_input()
        data["document"]["cumulative"]["cpa"] = "20,885"  # 월 CPA 25,641.03과 16,129.03의 단순 평균
        data["document"]["months"][0]["total"]["cpa"] = "25,833"  # 매체 CPA 25,000과 26,666.67의 단순 평균
        report = v.run(parse(data))
        self.assertEqual(find(report, "계약 누적 성과", "CPA")["status"], v.MISMATCH)
        self.assertEqual(find(report, "M1 성과 · 월 합계", "CPA")["status"], v.MISMATCH)

    def test_subtotal_components(self):
        data = base_input()
        data["document"]["months"][0]["allocation"].append(
            {"name": "A+B", "net_media": "1,000,000", "ratio_percent": "100.0", "components": ["A", "B"]})
        report = v.run(parse(data))
        self.assertEqual(find(report, "M1 배분", "A+B 소계")["status"], v.MATCH)
        self.assertEqual(find(report, "M1 배분", "매체 금액 합계")["status"], v.MATCH)


class MissingInput(unittest.TestCase):
    def test_missing_cpc_is_not_zero(self):
        data = base_input()
        del data["conditions"]["months"][0]["assumptions"][0]["cpc"]
        report = v.run(parse(data))
        for item in ("클릭", "전환", "매출", "CPA", "ROAS(%)"):
            self.assertEqual(find(report, "M1 성과 · A", item)["status"], v.MISSING_INPUT, item)
            self.assertEqual(find(report, "M1 성과 · 월 합계", item)["status"], v.MISSING_INPUT, item)
            self.assertEqual(find(report, "계약 누적 성과", item)["status"], v.MISSING_INPUT, item)
        self.assertFalse(report.passed())

    def test_missing_assumption_row(self):
        data = base_input()
        data["conditions"]["months"][1]["assumptions"].pop()
        report = v.run(parse(data))
        self.assertEqual(find(report, "M2 성과 · B", "CPC·CVR")["status"], v.MISSING_INPUT)

    def test_missing_budget_and_rate(self):
        data = base_input()
        data["conditions"]["months"][0]["billing_budget"] = ""
        data["conditions"]["vat_rate_percent"] = None
        report = v.run(parse(data))
        self.assertEqual(find(report, "M1 견적", "순매체비 역산")["status"], v.MISSING_INPUT)
        self.assertEqual(find(report, "M1 견적", "VAT")["status"], v.MISSING_INPUT)
        self.assertEqual(find(report, "조건", "VAT율(%)")["status"], v.MISSING_INPUT)

    def test_missing_document_value(self):
        data = base_input()
        del data["document"]["months"][1]["quote"]["vat"]
        del data["document"]["cumulative"]["roas_percent"]
        report = v.run(parse(data))
        self.assertEqual(find(report, "M2 견적", "VAT")["status"], v.MISSING_DOC)
        self.assertEqual(find(report, "계약 누적 성과", "ROAS(%)")["status"], v.MISSING_DOC)
        self.assertFalse(report.passed())

    def test_missing_display_unit(self):
        data = base_input()
        del data["document"]["display"]["clicks_decimals"]
        report = v.run(parse(data))
        self.assertEqual(find(report, "표시 단위", "clicks_decimals")["status"], v.MISSING_INPUT)
        self.assertEqual(find(report, "M1 성과 · A", "클릭")["status"], v.MISSING_INPUT)

    def test_missing_document_month(self):
        data = base_input()
        data["document"]["months"].pop()
        report = v.run(parse(data))
        self.assertEqual(find(report, "M2", "문서 월")["status"], v.MISSING_DOC)


class ZeroDenominator(unittest.TestCase):
    def test_zero_cvr(self):
        data = base_input()
        data["conditions"]["months"][0]["assumptions"][1]["cvr_percent"] = "0"
        data["document"]["months"][0]["media"][1]["conversions"] = "0"
        data["document"]["months"][0]["media"][1]["revenue"] = "0"
        data["document"]["months"][0]["media"][1]["cpa"] = "산출 불가"
        data["document"]["months"][0]["media"][1]["roas_percent"] = "0.0"
        report = v.run(parse(data))
        cpa = find(report, "M1 성과 · B", "CPA")
        self.assertEqual(cpa["status"], v.NOT_COMPUTABLE)  # 문서가 ‘산출 불가’로 적어도 통과가 아님
        self.assertIn("문서도 산출 불가", cpa["note"])
        self.assertEqual(find(report, "M1 성과 · B", "ROAS(%)")["status"], v.MATCH)
        self.assertFalse(report.passed())

    def test_marker_where_value_is_computable(self):
        data = base_input()
        data["document"]["months"][0]["media"][0]["cpa"] = "산출 불가"
        report = v.run(parse(data))
        self.assertEqual(find(report, "M1 성과 · A", "CPA")["status"], v.MISMATCH)

    def test_marker_in_amount_field_does_not_crash(self):
        data = base_input()
        data["document"]["months"][0]["quote"]["net_media"] = "산출 불가"
        data["document"]["months"][0]["allocation"][0]["net_media"] = "산출 불가"
        report = v.run(parse(data))
        self.assertEqual(find(report, "M1 견적", "수수료")["status"], v.NOT_COMPUTABLE)
        self.assertEqual(find(report, "M1 배분", "매체 금액 합계")["status"], v.NOT_COMPUTABLE)
        self.assertFalse(report.passed())

    def test_zero_cpc(self):
        data = base_input()
        data["conditions"]["months"][0]["assumptions"][0]["cpc"] = "0"
        report = v.run(parse(data))
        for item in ("클릭", "전환", "매출", "CPA", "ROAS(%)"):
            self.assertEqual(find(report, "M1 성과 · A", item)["status"], v.NOT_COMPUTABLE, item)

    def test_zero_net_media(self):
        p = v.performance(Decimal(0), Decimal(500), Decimal("0.02"), Decimal(30000), Decimal(1))
        r = v.ratios(p)
        self.assertIsInstance(r["cpa"], v.NotComputable)
        self.assertIsInstance(r["roas_percent"], v.NotComputable)

    def test_budget_without_integer_solution(self):
        # 수수료 10%·VAT 10%에서 청구액 1,210,005, 1,210,006을 만드는 정수 순매체비는 없다.
        self.assertEqual(v.solve_net_media(Decimal(1210006), Decimal("0.10"), Decimal("0.10")), [])
        data = base_input()
        data["conditions"]["months"][0]["billing_budget"] = "1,210,006"
        report = v.run(parse(data))
        self.assertEqual(find(report, "M1 견적", "순매체비(예산 역산)")["status"], v.NOT_COMPUTABLE)


class CommandLine(unittest.TestCase):
    def run_cli(self, data=None, raw=None):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "input.json")
            out = os.path.join(d, "result.json")
            with open(path, "w", encoding="utf-8") as f:
                f.write(raw if raw is not None else json.dumps(data, ensure_ascii=False))
            proc = subprocess.run([sys.executable, "-I", SCRIPT, "--input", path, "--json-out", out],
                                  capture_output=True, text=True)
            result = None
            if os.path.exists(out):
                with open(out, encoding="utf-8") as f:
                    result = json.load(f)
        return proc, result

    def test_exit_0_when_all_match(self):
        proc, result = self.run_cli(base_input())
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("종합: 전체 일치", proc.stdout)
        self.assertTrue(result["passed"])

    def test_exit_1_on_mismatch(self):
        data = base_input()
        data["document"]["contract_quote"]["billing"] = "2,420,001"
        proc, result = self.run_cli(data)
        self.assertEqual(proc.returncode, 1)
        self.assertFalse(result["passed"])

    def test_exit_2_on_bad_json(self):
        proc, _ = self.run_cli(raw="{ not json")
        self.assertEqual(proc.returncode, 2)
        self.assertIn("입력 오류", proc.stderr)

    def test_exit_2_on_non_numeric(self):
        data = base_input()
        data["conditions"]["unit_price"] = "삼만원"
        proc, _ = self.run_cli(data)
        self.assertEqual(proc.returncode, 2)


if __name__ == "__main__":
    unittest.main()
