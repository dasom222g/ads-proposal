# 광고 제안서·견적서 작성 지침

포커싱온이 고객사 무브펫의 광고 제안·견적을 작성하는 프로젝트다. 회사 기준과 고객 요구에 따라 전략·비용·기대 성과를 정리하고 금액과 근거를 검토한다.

## 입력 확인

- README와 회사 문서, 고객 브리프를 읽고 대행사·고객사, 계약 조건, 제출물을 확인한다.
- 사용자가 별도 회사 문서를 지정하면 해당 문서를 적용하고 실제 사용 경로를 기록한다. 예산·기간·수수료·VAT·성과 계산 입력·제출 범위가 미정이거나 충돌하면 원문과 계산 영향을 제시하고 필요한 결정부터 확인한다.
- 계정 기능·접근 권한·소재 수령처럼 집행 전 확인할 사항은 확인 시점과 조건부 실행 계획으로 남기고 제안서 작성을 계속한다.

## 문서 작성

- 한국어로 작성하고 Markdown 굵게 표시를 사용하지 않는다. 제공 조건과 계산 가정을 실제 집행 성과처럼 쓰지 않는다.
- 노트온 샘플은 형식만 참고한다. 샘플의 내용·수치·판정을 무브펫 결과나 근거로 복사하지 않는다.
- 요구사항·평가 기준을 정리할 때는 브리프·회사 문서·제출 양식의 요구를 원문 위치별로 추출하고 각각 검사 ID로 연결한다. 체크리스트 양식의 C01~C12에 요구를 연결하고, 같은 문제를 여러 항목으로 중복 집계하지 않는다. 원문에 연결되지 않은 기준이나 검사에 연결되지 않은 필수 요구가 있으면 기준 확정을 완료하지 않는다.
- 사용자 승인 없이 예산·업무 범위·판정 조건을 완화하지 않는다. 고객 제출 본문은 제안·견적 양식으로 작성하고 수정 전후와 평가 상태는 검토 기록에 남긴다.

## 결과 검토

- 확정한 체크리스트의 모든 항목을 검사한다. 초안과 요구사항의 원문 위치, 독립 재계산, 통과 항목 수와 실패 이유를 남긴다.
- 월 예산·계약 총액·수수료·VAT·매체 배분·CPA·ROAS는 브리프·회사 문서의 조건과 문서에 명시한 계산 전제를 바탕으로 독립 검산한다.
- 평가와 독립 검산을 함께 마친 뒤 통과·반려를 판정한다. 항목별로 `Y - 통과` 또는 `N - 반려`를 쓰며, 모든 항목이 Y일 때만 통과한다. 첫 평가부터 동일한 기준을 적용하고 모든 반려 사유를 한 번에 전달한다. 검사를 끝내지 못했으면 미완료로 구분한다. N이 있으면 문제 위치와 수정 요청을 기록하고 수정 후 전 항목을 재검사한다.
- 반려 후 재검사는 `제안서·견적서 — 반려 사항 수정 후 재검사`로 구분하고 이전 초안 대비 변경과 미해결 이슈를 남긴다. 실행하지 않은 검사를 완료로 기록하지 않는다.

### 검산 스크립트

- 경로: [artifacts/scripts/verify_quote_performance.py](artifacts/scripts/verify_quote_performance.py). 입력 형식과 계산 규칙은 [artifacts/scripts/README.md](artifacts/scripts/README.md)를 따른다.
- 계산이 필요한 평가·재평가마다 이 스크립트를 재사용한다. 이전 라운드의 입력을 복사하지 않고, 현재 평가 대상 초안의 값과 브리프·사규 조건으로 입력 JSON을 새로 만든다.
- 입력 형식: JSON의 `conditions`에는 브리프·사규의 수수료율·VAT율·판매가·구매당 수량·월 청구 예산·계약 총액·월별 매체 CPC·CVR을, `document`에는 초안의 표시 자릿수, 월별 견적·매체 배분·매체별 및 월 합계 성과, 계약 합계, 계약 누적 성과를 적는다. 초안에 없는 값은 비워 둔다.
- 실행: 프로젝트 루트에서 `python3 artifacts/scripts/verify_quote_performance.py --input artifacts/rounds/r{N}/verification-input.json --json-out artifacts/rounds/r{N}/verification-result.json`. 종료 코드 0은 모든 검산 일치, 1은 불일치·누락·계산 불가·확인 필요 있음, 2는 입력 오류다.
- 실행 근거는 해당 라운드 `evaluation.md`의 ‘견적·성과 독립 검산’에 스크립트 경로·실행 명령·입력 파일·종료 코드·검사 수와 불일치 항목으로 남긴다. 스크립트를 실행하지 못했거나 일부 수치를 검산하지 못했으면 판정을 미완료로 기록한다.
- 스크립트를 수정하면 `python3 -m unittest artifacts/scripts/test_verify_quote_performance.py`로 다시 확인한다. 코드에 특정 고객의 수치나 정답을 넣지 않는다.

## 산출물과 저장

- 파일명·저장 위치와 라운드 번호는 README의 문서 저장 규칙을 따른다. 원자료·양식·샘플과 평가받은 초안·이전 라운드를 보존한다. 제안과 견적은 한 초안으로 완성하고, 수정 전후 내역은 고객 본문이 아닌 해당 라운드 평가에 기록한다.
- 현재 초안을 요구사항 정의서와 체크리스트의 전 항목으로 평가·검산한다. 재작업·재평가만 요청받으면 라운드 기록만 남기고, 최종 산출물 작성이 요청된 경우에만 통과본과 교차 검토 보고서를 Markdown·HTML로 저장한다.
- 평가 기록에 대상 라운드와 초안 경로를 명시한다. 요구사항·평가 기준 또는 초안의 업무 내용이 바뀌면 이전 판정을 그대로 적용하지 않고 전 항목을 재검사한다. 이전 파일은 보존하고 해당 라운드 평가에 판정과 미해결 사항을 남긴다.
- 교차 검토 보고서는 양식에 따라 이번 작업의 전체 라운드와 최종 판정을 종합한다. 첫 초안과 최종본의 변경 이유를 실제 반려·수정·재평가 기록에 연결한다.
- 최종 HTML의 범위와 링크 검사는 README의 ‘최종 문서의 HTML’을 따른다. 디자인 참고 파일의 스타일을 적용하고 내용은 최종 Markdown에 맞춘다. 두 문서의 모든 내부 링크를 실제로 열어 대상 파일·구역을 확인하고, 수정 후 재확인한다.
- `CLAUDE.md`는 `AGENTS.md`를 가리키는 상대 심볼릭 링크로 유지한다.

## 참고자료

- 프로젝트 구조·저장 규칙: [README.md](README.md)
- 회사 소개서: [about-company.md](docs/about-company.md)
- 업무 사규: [company-rules.md](docs/company-rules.md)
- 회사 작업 지침: [project-instructions.md](docs/project-instructions.md)
- 고객 브리프: [brief.md](sources/brief.md)
- 제안·견적 양식: [proposal-quote-template.md](references/templates/proposal-quote-template.md)
- 요구사항·검사 양식: [요구사항](references/templates/requirements-template.md), [체크리스트](references/templates/evaluation-checklist-template.md), [평가](references/templates/evaluation-template.md)
- 교차 검토 보고서: [양식](references/templates/cross-review-report-template.md), [샘플](references/samples/cross-review-report-sample.md)
- HTML 디자인: [제안서](references/design/proposal-quote.html), [교차 검토 보고서](references/design/cross-review-report.html)
- 평가 기록 샘플: [evaluation-sample.md](references/samples/evaluation-sample.md)
- 작성 예시: [references/samples/](references/samples/)
- 요구사항·검사 기록: [artifacts/rules/](artifacts/rules/), [artifacts/rounds/](artifacts/rounds/) — 작업 중 생성
- 검산 스크립트: [artifacts/scripts/](artifacts/scripts/)
