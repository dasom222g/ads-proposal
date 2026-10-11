#!/usr/bin/env python3
"""제안서·견적서의 금액과 예상 성과를 독립 재계산해 문서 값과 비교한다.

실행: python3 artifacts/scripts/verify_quote_performance.py --input <입력.json> [--json-out <결과.json>]

입력 JSON은 실행할 때마다 브리프·사규 조건(conditions)과 검산할 문서 값(document)을 받는다.
형식은 artifacts/scripts/README.md를 따른다. 특정 고객의 수치나 정답은 코드에 두지 않는다.

계산 규칙
- 원 단위·표시값 반올림은 0.5 이상 올림(ROUND_HALF_UP)이다.
- 수수료=round(월 순매체비×수수료율), VAT=round((월 순매체비+수수료)×VAT율), 월 청구액=공급가액+VAT.
- 계약 합계는 월별 재계산 값의 합이다.
- 클릭=순매체비÷CPC, 전환=클릭×CVR, 매출=전환×구매당 수량×판매가, CPA=순매체비÷전환,
  ROAS=매출÷순매체비×100. 중간값은 반올림하지 않고, 월 합계·누적은 반올림 전 합산값으로 계산한다.
- 성과 표시 단위: 전환 소수 둘째 자리, CPA 원 단위, ROAS 소수 첫째 자리.
  클릭·매출·배분 비율의 표시 자릿수는 입력의 document.display에서 받는다.

종료 코드: 0 모든 검사 일치, 1 불일치·누락·계산 불가·확인 필요가 있음, 2 입력 파일·형식 오류.
"""

import argparse
import json
import sys
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

FIXED_DECIMALS = {"conversions": 2, "cpa": 0, "roas_percent": 1}
MONEY_DECIMALS = 0
QUOTE_FIELDS = ["net_media", "fee", "supply", "vat", "billing"]
PERF_FIELDS = ["clicks", "conversions", "revenue", "cpa", "roas_percent"]
LABELS = {
    "net_media": "순매체비", "fee": "수수료", "supply": "공급가액", "vat": "VAT",
    "billing": "청구 총액", "clicks": "클릭", "conversions": "전환", "revenue": "매출",
    "cpa": "CPA", "roas_percent": "ROAS(%)", "ratio_percent": "비율(%)",
}

MATCH = "일치"
MISMATCH = "불일치"
MISSING_INPUT = "입력 누락"
MISSING_DOC = "문서 값 누락"
NOT_COMPUTABLE = "계산 불가"
REVIEW = "확인 필요"


class InputError(Exception):
    pass


class Missing:
    """입력이 없어 계산하지 않은 값. 0으로 대체하지 않는다."""

    def __init__(self, what):
        self.what = what


class NotComputable:
    """분모가 0이거나 선행 값이 계산 불가라서 산출할 수 없는 값."""

    def __init__(self, why):
        self.why = why


class DocNotComputable:
    """문서가 ‘산출 불가’로 표시한 값. 숫자로 바꾸지 않는다."""

    def __init__(self, text):
        self.text = text


NOT_COMPUTABLE_MARKS = {"산출 불가", "산출불가", "계산 불가", "계산불가"}


def is_value(x):
    return isinstance(x, Decimal)


def parse_number(raw, where):
    """숫자 또는 숫자 문자열(쉼표 허용)을 Decimal로 바꾼다. 없거나 빈 값은 Missing."""
    if raw is None:
        return Missing(where)
    if isinstance(raw, bool):
        raise InputError(f"{where}: 숫자가 아닌 값 {raw!r}")
    if isinstance(raw, (int, Decimal)):
        return Decimal(raw)
    if isinstance(raw, float):
        return Decimal(str(raw))
    if isinstance(raw, str):
        text = raw.strip().replace(",", "")
        if text == "":
            return Missing(where)
        if text in NOT_COMPUTABLE_MARKS:
            return DocNotComputable(text)
        try:
            value = Decimal(text)
        except InvalidOperation:
            raise InputError(f"{where}: 숫자로 읽을 수 없는 값 {raw!r}")
        if not value.is_finite():
            raise InputError(f"{where}: 유한한 숫자가 아님 {raw!r}")
        return value
    raise InputError(f"{where}: 숫자가 아닌 값 {raw!r}")


def get_number(obj, key, where):
    if not isinstance(obj, dict):
        return Missing(f"{where}.{key}")
    return parse_number(obj.get(key), f"{where}.{key}")


def round_to(value, decimals):
    quantum = Decimal(1).scaleb(-int(decimals))
    return value.quantize(quantum, rounding=ROUND_HALF_UP)


def as_operand(v):
    """문서의 ‘산출 불가’ 표시는 계산 입력으로 쓰지 않는다."""
    return NotComputable("문서 값이 산출 불가 표시") if isinstance(v, DocNotComputable) else v


def div(numerator, denominator, why):
    numerator, denominator = as_operand(numerator), as_operand(denominator)
    for v in (numerator, denominator):
        if isinstance(v, (Missing, NotComputable)):
            return v
    if denominator == 0:
        return NotComputable(why)
    return numerator / denominator


def mul(*values):
    result = Decimal(1)
    for v in map(as_operand, values):
        if isinstance(v, (Missing, NotComputable)):
            return v
        result *= v
    return result


def add_all(values):
    total = Decimal(0)
    for v in map(as_operand, values):
        if isinstance(v, (Missing, NotComputable)):
            return v
        total += v
    return total


def fmt(value):
    if isinstance(value, Missing):
        return f"없음({value.what})"
    if isinstance(value, NotComputable):
        return f"계산 불가({value.why})"
    if isinstance(value, DocNotComputable):
        return value.text
    if value is None:
        return "-"
    text = format(value.normalize(), "f") if value == value.to_integral() else format(value, "f")
    if "." in text:
        whole, frac = text.split(".")
        frac = frac.rstrip("0")
        if len(frac) > 10:
            frac = frac[:10] + "…"
    else:
        whole, frac = text, ""
    sign = "-" if whole.startswith("-") else ""
    whole = whole.lstrip("-")
    whole = f"{int(whole):,}"
    return f"{sign}{whole}.{frac}" if frac else f"{sign}{whole}"


class Report:
    def __init__(self):
        self.checks = []

    def add(self, section, item, status, document=None, computed=None, unrounded=None, note=""):
        self.checks.append({
            "section": section, "item": item, "status": status,
            "document": fmt(document) if document is not None else "-",
            "computed": fmt(computed) if computed is not None else "-",
            "unrounded": fmt(unrounded) if unrounded is not None else "-",
            "note": note,
        })

    def compare(self, section, item, doc_value, computed, decimals, note=""):
        """반올림 전 재계산 값을 표시 단위로 반올림해 문서 값과 비교한다."""
        if isinstance(computed, Missing):
            self.add(section, item, MISSING_INPUT, doc_value, computed, note=note)
            return
        if isinstance(computed, NotComputable):
            # 계산할 수 없는 값은 문서가 ‘산출 불가’로 적었더라도 통과로 처리하지 않는다.
            marked = "문서도 산출 불가로 표시. " if isinstance(doc_value, DocNotComputable) else ""
            self.add(section, item, NOT_COMPUTABLE, doc_value, computed,
                     note=marked + (note or "평가자가 문서의 0 분모 처리 설명을 확인"))
            return
        shown = round_to(computed, decimals)
        if isinstance(doc_value, Missing):
            self.add(section, item, MISSING_DOC, doc_value, shown, computed, note)
            return
        status = MATCH if is_value(doc_value) and doc_value == shown else MISMATCH
        self.add(section, item, status, doc_value, shown, computed, note)

    def passed(self):
        return all(c["status"] == MATCH for c in self.checks)

    def counts(self):
        out = {}
        for c in self.checks:
            out[c["status"]] = out.get(c["status"], 0) + 1
        return out


def load_input(path):
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f, parse_float=Decimal, parse_int=Decimal)
    except OSError as e:
        raise InputError(f"입력 파일을 열 수 없음: {e}")
    except json.JSONDecodeError as e:
        raise InputError(f"JSON 형식 오류: {e}")
    if not isinstance(data, dict):
        raise InputError("최상위 값은 객체여야 함")
    for key in ("conditions", "document"):
        if not isinstance(data.get(key), dict):
            raise InputError(f"'{key}' 객체가 필요함")
    for key in ("months",):
        if not isinstance(data["conditions"].get(key), list) or not data["conditions"][key]:
            raise InputError("conditions.months 목록이 필요함")
        if not isinstance(data["document"].get(key), list) or not data["document"][key]:
            raise InputError("document.months 목록이 필요함")
    return data


def solve_net_media(budget, fee_rate, vat_rate):
    """월 청구 예산을 정확히 만드는 정수 순매체비를 모두 찾는다."""
    if not budget > 0:
        return []
    approx = (budget / ((1 + fee_rate) * (1 + vat_rate))).to_integral_value(rounding="ROUND_FLOOR")
    window = 50
    found = []
    for m in range(max(0, int(approx) - window), int(approx) + window + 1):
        net = Decimal(m)
        fee = round_to(net * fee_rate, MONEY_DECIMALS)
        vat = round_to((net + fee) * vat_rate, MONEY_DECIMALS)
        if net + fee + vat == budget:
            found.append(net)
    return found


def quote_from_net(net, fee_rate, vat_rate):
    """문서의 월 순매체비로 수수료·공급가액·VAT·청구액을 계산한다. (반올림 전 값, 원 단위 값)"""
    net = as_operand(net)
    if not is_value(net) or not is_value(fee_rate):
        miss = fee_rate if is_value(net) else net
        return {k: (miss, miss) for k in QUOTE_FIELDS[1:]}
    fee_raw = net * fee_rate
    fee = round_to(fee_raw, MONEY_DECIMALS)
    supply = net + fee
    if not is_value(vat_rate):
        return {"fee": (fee_raw, fee), "supply": (supply, supply),
                "vat": (vat_rate, vat_rate), "billing": (vat_rate, vat_rate)}
    vat_raw = supply * vat_rate
    vat = round_to(vat_raw, MONEY_DECIMALS)
    billing = supply + vat
    return {"fee": (fee_raw, fee), "supply": (supply, supply),
            "vat": (vat_raw, vat), "billing": (billing, billing)}


def performance(net, cpc, cvr_rate, unit_price, units):
    clicks = div(net, cpc, "CPC 0")
    conversions = mul(clicks, cvr_rate)
    revenue = mul(conversions, units, unit_price)
    return {"net_media": net, "clicks": clicks, "conversions": conversions, "revenue": revenue}


def ratios(totals):
    net, conv, rev = totals["net_media"], totals["conversions"], totals["revenue"]
    cpa = div(net, conv, "전환 0")
    roas = div(rev, net, "순매체비 0")
    roas = mul(roas, Decimal(100)) if is_value(roas) else roas
    return {"cpa": cpa, "roas_percent": roas}


def sum_perf(rows):
    return {k: add_all([r[k] for r in rows]) for k in ("net_media", "clicks", "conversions", "revenue")}


def perf_decimals(display):
    decimals = dict(FIXED_DECIMALS)
    decimals["clicks"] = display.get("clicks_decimals")
    decimals["revenue"] = display.get("revenue_decimals")
    return decimals


def compare_perf(report, section, doc_row, computed, decimals):
    for key in ["net_media"] + PERF_FIELDS:
        d = MONEY_DECIMALS if key == "net_media" else decimals[key]
        doc_value = get_number(doc_row, key, section)
        if d is None:
            report.add(section, LABELS[key], MISSING_INPUT,
                       note=f"document.display의 {key}_decimals 표시 자릿수가 없음")
            continue
        report.compare(section, LABELS[key], doc_value, computed[key], d)


def run(data):
    report = Report()
    cond = data["conditions"]
    doc = data["document"]

    fee_pct = get_number(cond, "fee_rate_percent", "conditions")
    vat_pct = get_number(cond, "vat_rate_percent", "conditions")
    fee_rate = fee_pct / 100 if is_value(fee_pct) else fee_pct
    vat_rate = vat_pct / 100 if is_value(vat_pct) else vat_pct
    unit_price = get_number(cond, "unit_price", "conditions")
    units = get_number(cond, "units_per_purchase", "conditions")
    contract_budget = get_number(cond, "contract_total_budget", "conditions")
    for name, value in (("수수료율(%)", fee_pct), ("VAT율(%)", vat_pct), ("판매가", unit_price),
                        ("구매당 수량", units), ("계약 총액 예산", contract_budget)):
        if isinstance(value, Missing):
            report.add("조건", name, MISSING_INPUT, note=value.what)

    display = doc.get("display") if isinstance(doc.get("display"), dict) else {}
    decimals = perf_decimals(display)
    ratio_decimals = display.get("ratio_percent_decimals")
    for key in ("clicks_decimals", "revenue_decimals", "ratio_percent_decimals"):
        if display.get(key) is None:
            report.add("표시 단위", key, MISSING_INPUT, note="문서에 밝힌 표시 자릿수를 document.display에 입력")
    for key in ("clicks", "revenue"):
        if decimals[key] is not None:
            decimals[key] = int(decimals[key])
    if ratio_decimals is not None:
        ratio_decimals = int(ratio_decimals)

    cond_months = {}
    for i, m in enumerate(cond["months"]):
        name = m.get("month") if isinstance(m, dict) else None
        if not name:
            raise InputError(f"conditions.months[{i}].month 이름이 필요함")
        if name in cond_months:
            raise InputError(f"conditions.months에 같은 월 이름이 반복됨: {name}")
        cond_months[name] = m

    doc_month_names = []
    contract_quote = {k: [] for k in QUOTE_FIELDS}
    all_perf_rows = []

    for i, dm in enumerate(doc["months"]):
        if not isinstance(dm, dict) or not dm.get("month"):
            raise InputError(f"document.months[{i}].month 이름이 필요함")
        month = dm["month"]
        doc_month_names.append(month)
        cm = cond_months.get(month)
        if cm is None:
            report.add(month, "브리프 조건", MISSING_INPUT, note="conditions.months에 같은 이름의 월이 없음")
            cm = {}

        # 견적: 월 청구 예산에서 순매체비 역산
        budget = get_number(cm, "billing_budget", f"conditions.{month}")
        quote_doc = dm.get("quote") if isinstance(dm.get("quote"), dict) else {}
        doc_net = get_number(quote_doc, "net_media", f"document.{month}.quote")
        section = f"{month} 견적"
        if isinstance(budget, Missing) or isinstance(fee_rate, Missing) or isinstance(vat_rate, Missing):
            report.add(section, "순매체비 역산", MISSING_INPUT,
                       note="월 청구 예산·수수료율·VAT율이 모두 필요함")
        else:
            solutions = solve_net_media(budget, fee_rate, vat_rate)
            if len(solutions) == 1:
                report.compare(section, "순매체비(예산 역산)", doc_net, solutions[0], MONEY_DECIMALS,
                               note=f"월 청구 예산 {fmt(budget)}원을 만족하는 유일한 정수 순매체비")
            elif not solutions:
                report.add(section, "순매체비(예산 역산)", NOT_COMPUTABLE, doc_net,
                           note=f"월 청구 예산 {fmt(budget)}원을 정확히 만드는 정수 순매체비가 없음. 사용자 결정 필요")
            else:
                report.add(section, "순매체비(예산 역산)", REVIEW, doc_net,
                           note="예산을 만족하는 순매체비가 여러 개: " + ", ".join(fmt(s) for s in solutions))

        # 견적: 문서의 순매체비로 수수료·VAT·청구액 재계산
        computed_quote = quote_from_net(doc_net, fee_rate, vat_rate)
        contract_quote["net_media"].append(doc_net)
        for key in QUOTE_FIELDS[1:]:
            raw, shown = computed_quote[key]
            contract_quote[key].append(shown)
            doc_value = get_number(quote_doc, key, f"document.{month}.quote")
            if isinstance(shown, Missing):
                report.add(section, LABELS[key], MISSING_INPUT, doc_value, shown)
            elif isinstance(shown, NotComputable):
                report.add(section, LABELS[key], NOT_COMPUTABLE, doc_value, shown)
            elif isinstance(doc_value, Missing):
                report.add(section, LABELS[key], MISSING_DOC, doc_value, shown, raw)
            else:
                report.add(section, LABELS[key], MATCH if is_value(doc_value) and doc_value == shown else MISMATCH,
                           doc_value, shown, raw)
        billing_shown = computed_quote["billing"][1]
        if is_value(billing_shown) and is_value(budget):
            report.add(section, "청구 총액과 월 예산", MATCH if billing_shown == budget else MISMATCH,
                       budget, billing_shown, note="재계산 청구액이 브리프 월 청구 예산과 같은지")

        # 배분: 매체 금액 합계·비율
        alloc = dm.get("allocation")
        section = f"{month} 배분"
        if not isinstance(alloc, list) or not alloc:
            report.add(section, "매체 배분", MISSING_DOC, note="document.months[].allocation 목록이 없음")
        else:
            by_name = {}
            leaf_values = []
            for j, row in enumerate(alloc):
                if not isinstance(row, dict) or not row.get("name"):
                    raise InputError(f"document.{month}.allocation[{j}].name 이 필요함")
                by_name[row["name"]] = row
            for row in alloc:
                net = get_number(row, "net_media", f"document.{month}.allocation.{row['name']}")
                comps = row.get("components")
                if comps:
                    parts = []
                    for c in comps:
                        if c not in by_name:
                            parts.append(Missing(f"allocation에 '{c}' 없음"))
                        else:
                            parts.append(get_number(by_name[c], "net_media", f"document.{month}.allocation.{c}"))
                    report.compare(section, f"{row['name']} 소계", net, add_all(parts), MONEY_DECIMALS,
                                   note="구성 매체 금액의 합")
                else:
                    leaf_values.append(net)
                ratio_doc = get_number(row, "ratio_percent", f"document.{month}.allocation.{row['name']}")
                if ratio_decimals is None:
                    report.add(section, f"{row['name']} 비율(%)", MISSING_INPUT, ratio_doc,
                               note="ratio_percent_decimals 없음")
                else:
                    ratio = mul(div(net, doc_net, "월 순매체비 0"), Decimal(100))
                    report.compare(section, f"{row['name']} 비율(%)", ratio_doc, ratio, ratio_decimals,
                                   note="매체 금액÷문서 월 순매체비×100")
            leaf_sum = add_all(leaf_values)
            report.compare(section, "매체 금액 합계", doc_net, leaf_sum, MONEY_DECIMALS,
                           note="구성 매체(소계 행 제외) 금액 합계와 문서 월 순매체비 비교")
            ratio_values = [get_number(r, "ratio_percent", "") for r in alloc if not r.get("components")]
            ratio_sum = add_all(ratio_values)
            if is_value(ratio_sum):
                report.add(section, "표시 비율 합계(%)", MATCH if ratio_sum == 100 else REVIEW,
                           ratio_sum, Decimal(100),
                           note="" if ratio_sum == 100 else "표시 반올림 차이인지 문서 설명 확인")

        # 성과: 매체별, 월 합계
        assumptions = {}
        for a in cm.get("assumptions", []) if isinstance(cm.get("assumptions"), list) else []:
            if isinstance(a, dict) and a.get("media"):
                assumptions[a["media"]] = a
        perf_rows_doc = dm.get("media") if isinstance(dm.get("media"), list) else []
        if not perf_rows_doc:
            report.add(f"{month} 성과", "매체별 성과", MISSING_DOC, note="document.months[].media 목록이 없음")
        month_rows = []
        for row in perf_rows_doc:
            media = row.get("media") if isinstance(row, dict) else None
            if not media:
                raise InputError(f"document.{month}.media 항목에 media 이름이 필요함")
            section = f"{month} 성과 · {media}"
            a = assumptions.get(media)
            if a is None:
                report.add(section, "CPC·CVR", MISSING_INPUT,
                           note=f"conditions.{month}.assumptions에 '{media}' 입력이 없음")
                a = {}
            cpc = get_number(a, "cpc", f"conditions.{month}.{media}")
            cvr_pct = get_number(a, "cvr_percent", f"conditions.{month}.{media}")
            cvr_rate = cvr_pct / 100 if is_value(cvr_pct) else cvr_pct
            net = get_number(row, "net_media", f"document.{month}.media.{media}")
            computed = performance(net, cpc, cvr_rate, unit_price, units)
            month_rows.append(computed)
            computed.update(ratios(computed))
            compare_perf(report, section, row, computed, decimals)
        if month_rows:
            totals = sum_perf(month_rows)
            totals.update(ratios(totals))
            compare_perf(report, f"{month} 성과 · 월 합계", dm.get("total"), totals, decimals)
            report.compare(f"{month} 성과 · 월 합계", "성과 순매체비와 견적 순매체비", doc_net,
                           totals["net_media"], MONEY_DECIMALS, note="성과 계산 순매체비 합계가 견적 월 순매체비와 같은지")
            all_perf_rows.extend(month_rows)

    for name in cond_months:
        if name not in doc_month_names:
            report.add(name, "문서 월", MISSING_DOC, note="브리프 조건의 월이 문서 입력에 없음")

    # 계약 합계
    section = "계약 합계"
    contract_doc = doc.get("contract_quote") if isinstance(doc.get("contract_quote"), dict) else {}
    for key in QUOTE_FIELDS:
        total = add_all(contract_quote[key])
        report.compare(section, LABELS[key], get_number(contract_doc, key, "document.contract_quote"),
                       total, MONEY_DECIMALS, note="월별 재계산 값의 합" if key != "net_media" else "문서 월 순매체비의 합")
    contract_billing = add_all(contract_quote["billing"])
    if is_value(contract_billing) and is_value(contract_budget):
        report.add(section, "청구 총액과 계약 총액 예산", MATCH if contract_billing == contract_budget else MISMATCH,
                   contract_budget, contract_billing, note="월 청구액 합이 브리프 계약 총액과 같은지")

    # 계약 누적 성과
    if all_perf_rows:
        totals = sum_perf(all_perf_rows)
        totals.update(ratios(totals))
        compare_perf(report, "계약 누적 성과", doc.get("cumulative"), totals, decimals)

    return report


def print_report(report, label):
    print(f"# 검산 결과{(' — ' + label) if label else ''}")
    print()
    print("| 구분 | 항목 | 판정 | 문서 값 | 재계산 표시값 | 반올림 전 값 | 비고 |")
    print("| --- | --- | --- | --- | --- | --- | --- |")
    for c in report.checks:
        print(f"| {c['section']} | {c['item']} | {c['status']} | {c['document']} | {c['computed']} | "
              f"{c['unrounded']} | {c['note']} |")
    print()
    counts = report.counts()
    summary = ", ".join(f"{k} {v}" for k, v in counts.items())
    verdict = "전체 일치" if report.passed() else "불일치·미확인 있음"
    print(f"- 검사 수: {len(report.checks)} ({summary})")
    print(f"- 종합: {verdict}")


def main(argv=None):
    parser = argparse.ArgumentParser(description="제안서·견적서 금액·예상 성과 독립 검산")
    parser.add_argument("--input", required=True, help="조건과 문서 값을 담은 JSON 파일")
    parser.add_argument("--json-out", help="검사 결과를 JSON으로 저장할 경로")
    args = parser.parse_args(argv)
    try:
        data = load_input(args.input)
        report = run(data)
    except InputError as e:
        print(f"입력 오류: {e}", file=sys.stderr)
        return 2
    label = data.get("label") if isinstance(data.get("label"), str) else ""
    print_report(report, label)
    if args.json_out:
        with open(args.json_out, "w", encoding="utf-8") as f:
            json.dump({"label": label, "passed": report.passed(), "counts": report.counts(),
                       "checks": report.checks}, f, ensure_ascii=False, indent=2)
    return 0 if report.passed() else 1


if __name__ == "__main__":
    sys.exit(main())
