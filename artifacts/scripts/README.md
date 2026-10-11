# 검산 스크립트

제안서·견적서의 금액과 예상 성과를 독립 재계산하고 문서 값과 비교합니다. Python 3 표준 라이브러리만 사용합니다.

| 파일 | 용도 |
| --- | --- |
| `verify_quote_performance.py` | 검산 스크립트 |
| `test_verify_quote_performance.py` | 정상값·불일치·반올림·누적 계산·입력 누락·분모 0 동작 확인 |
| `input-example.json` | 입력 형식 예시. 가상 수치이며 특정 고객의 값이 아님 |

## 실행

프로젝트 루트에서 실행합니다.

```sh
python3 artifacts/scripts/verify_quote_performance.py \
  --input artifacts/rounds/r{N}/verification-input.json \
  --json-out artifacts/rounds/r{N}/verification-result.json
```

- 표준 출력에 검사 표(구분·항목·판정·문서 값·재계산 표시값·반올림 전 값·비고)와 검사 수·종합 결과가 나옵니다.
- 종료 코드: `0` 모든 검사 일치, `1` 불일치·입력 누락·문서 값 누락·계산 불가·확인 필요가 하나 이상 있음, `2` 입력 파일·형식 오류.
- 동작 확인: `python3 -m unittest artifacts/scripts/test_verify_quote_performance.py -v`

## 계산 규칙

- 원 단위·표시값 반올림은 0.5 이상 올림(ROUND_HALF_UP)입니다.
- 순매체비 역산: 월 청구 예산 B에 대해 `M + round(M×수수료율) + round((M + round(M×수수료율))×VAT율) = B`를 만족하는 정수 M을 모두 찾습니다. 하나면 문서 순매체비와 비교하고, 없으면 계산 불가, 여러 개면 확인 필요로 표시합니다.
- 견적: 문서의 월 순매체비로 수수료=round(순매체비×수수료율), 공급가액=순매체비+수수료, VAT=round(공급가액×VAT율), 청구액=공급가액+VAT를 계산합니다. 재계산 청구액을 월 청구 예산과 비교합니다.
- 계약 합계: 월별 재계산 값(순매체비·수수료·공급가액·VAT·청구액)의 합입니다. 청구액 합을 계약 총액 예산과 비교합니다.
- 배분: 구성 매체 금액의 합이 문서 월 순매체비와 같은지, 각 비율이 매체 금액÷월 순매체비×100을 표시 자릿수로 반올림한 값과 같은지, 소계 행이 구성 매체의 합과 같은지 확인합니다. 표시 비율 합계가 100이 아니면 확인 필요로 표시합니다.
- 성과: 클릭=순매체비÷CPC, 전환=클릭×CVR, 매출=전환×구매당 수량×판매가, CPA=순매체비÷전환, ROAS=매출÷순매체비×100. 중간값은 반올림하지 않습니다. 월 합계·계약 누적은 반올림 전 순매체비·클릭·전환·매출을 합산해 CPA·ROAS를 다시 계산합니다.
- 성과 표시 단위는 전환 소수 둘째 자리, CPA 원 단위, ROAS 소수 첫째 자리로 고정합니다. 클릭·매출·배분 비율의 자릿수는 문서가 밝힌 값을 `document.display`에 입력합니다.
- 입력 누락은 0으로 대체하지 않고 `입력 누락`·`문서 값 누락`으로 표시합니다. 분모가 0이면 `계산 불가`이며, 문서가 `산출 불가`로 적었더라도 통과로 처리하지 않습니다. 평가자가 문서의 0 분모 처리 설명을 따로 확인합니다.

## 입력 형식

숫자는 JSON 숫자 또는 숫자 문자열로 적습니다. 문자열의 쉼표는 허용하지만 `원`·`%` 같은 단위는 적지 않습니다. 성과 값이 문서에 `산출 불가`로 적혀 있으면 그 문자열을 그대로 입력합니다.

```json
{
  "label": "r{N} draft.md 검산",
  "conditions": {
    "fee_rate_percent": "브리프·사규의 수수료율(%)",
    "vat_rate_percent": "VAT율(%)",
    "unit_price": "판매가(원)",
    "units_per_purchase": "구매당 수량",
    "contract_total_budget": "계약 총액(원, VAT 포함)",
    "months": [
      {
        "month": "월 이름(문서와 같은 이름)",
        "billing_budget": "월 청구 예산(원, VAT 포함)",
        "assumptions": [
          {"media": "매체 이름(문서 성과 행과 같은 이름)", "cpc": "CPC(원)", "cvr_percent": "CVR(%)"}
        ]
      }
    ]
  },
  "document": {
    "display": {"clicks_decimals": 2, "revenue_decimals": 0, "ratio_percent_decimals": 1},
    "months": [
      {
        "month": "월 이름",
        "quote": {"net_media": "", "fee": "", "supply": "", "vat": "", "billing": ""},
        "allocation": [
          {"name": "매체", "net_media": "", "ratio_percent": ""},
          {"name": "소계 행", "net_media": "", "ratio_percent": "", "components": ["소계에 포함된 매체 이름"]}
        ],
        "media": [
          {"media": "매체 이름", "net_media": "", "clicks": "", "conversions": "", "revenue": "", "cpa": "", "roas_percent": ""}
        ],
        "total": {"net_media": "", "clicks": "", "conversions": "", "revenue": "", "cpa": "", "roas_percent": ""}
      }
    ],
    "contract_quote": {"net_media": "", "fee": "", "supply": "", "vat": "", "billing": ""},
    "cumulative": {"net_media": "", "clicks": "", "conversions": "", "revenue": "", "cpa": "", "roas_percent": ""}
  }
}
```

- `conditions`: 브리프·업무 사규의 조건만 적습니다. 문서에 적힌 조건을 옮겨 적지 않습니다.
- `document`: 평가 대상 초안에 적힌 값만 적습니다. 문서에 없는 값은 비워 두면 `문서 값 누락`으로 표시됩니다.
- `allocation`: 소계 행(`components`가 있는 행)은 매체 금액 합계에서 제외하고 구성 매체의 합과만 비교합니다.
- `media`: 성과 가정이 제공된 단위(예: 매체 합산)로 적고, `media` 이름을 `assumptions`의 이름과 맞춥니다.
- 완성된 예시는 [input-example.json](input-example.json)을 참고합니다.
