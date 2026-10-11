# 광고 제안서·견적서

광고대행사 포커싱온이 무브펫의 광고 전략과 견적을 제안하는 프로젝트입니다. 회사 문서·고객 브리프·문서 양식을 바탕으로 제안서를 작성하고, 고객 요구와 금액 계산을 검토합니다.

작업 지침은 [AGENTS.md](AGENTS.md)를 따릅니다. `CLAUDE.md`는 같은 지침을 가리키는 링크입니다.

## 폴더 구조

```text
ads-proposal/
├── docs/                # 회사 업무 기준
├── sources/             # 고객 의뢰 자료
├── references/          # 양식·샘플·HTML 디자인
│   ├── templates/       # 문서 양식
│   ├── samples/         # 작성 샘플
│   └── design/          # HTML 스타일·문서 간 이동
├── prompts/             # 전체 루프 실행 프롬프트
└── artifacts/           # 에이전트 산출물
    ├── rules/           # 요구사항·평가 기준
    ├── scripts/         # 금액·예상 성과 검산 스크립트와 동작 확인 테스트
    ├── rounds/          # 라운드별 초안·평가·검산 입력과 결과·수정 요청
    └── final/           # 최종 제안서·교차 검토 보고서
```

[고객 브리프](sources/brief.md)에서 광고 목표·계약 조건·계산 입력을 확인합니다.

별도 회사 문서를 지정하면 해당 문서를 적용합니다. 원자료·양식·샘플은 결과물로 덮어쓰지 않습니다.

## 전체 루프 실행

요구사항·체크리스트·검산 스크립트를 준비한 뒤 [전체 루프 실행 프롬프트](prompts/loop.md)를 사용합니다.

## 문서 저장

경로는 프로젝트 루트 기준이며, `{N}`은 검토 차수입니다. 라운드 폴더는 `r1`, `r2` 순서로 만듭니다.

- 제안 부분과 견적 부분은 같은 `draft.md`에 작성합니다. 첫 평가 전까지는 같은 파일을 완성합니다.
- 평가받은 초안은 보존합니다. 반려 후 수정하거나 새 초안을 작성할 때는 기존 최대 번호 다음의 라운드 폴더를 사용합니다.
- 초안·평가·수정 요청은 같은 라운드에 모읍니다. 수정 전후 내역은 `evaluation.md`의 ‘이전 검토 대비 변화’에 기록하며, 반려 항목이 있으면 평가 기록의 반려 사유·수정 요청을 `revision-request.md`로 전달합니다.
- 재작업·재평가만 요청받으면 통과 여부와 관계없이 라운드 기록만 저장합니다. 최종 산출물 작성까지 요청받고 전 항목이 통과했을 때 최종 제안서와 교차 검토 보고서를 Markdown·HTML로 저장합니다.
- 교차 검토 보고서는 이번 작업의 시작·종료 라운드, 라운드별 판정·통과 수, 반려와 수정 과정, 첫 초안과 최종본의 차이, 최종 판정과 남은 확인 사항을 종합합니다. 이전 라운드 기록은 보존합니다.

| 문서 | 저장 위치 |
| --- | --- |
| 요구사항 정의서 | `artifacts/rules/requirements.md` |
| 평가 체크리스트 | `artifacts/rules/evaluation-checklist.md` |
| 검산 스크립트 | `artifacts/scripts/verify_quote_performance.py` |
| 검산 스크립트 입력 형식·동작 확인 | `artifacts/scripts/README.md`, `artifacts/scripts/test_verify_quote_performance.py` |
| 제안·견적 초안 | `artifacts/rounds/r{N}/draft.md` |
| 평가·검산·수정 전후 내역 | `artifacts/rounds/r{N}/evaluation.md` |
| 검산 입력·결과 | `artifacts/rounds/r{N}/verification-input.json`, `artifacts/rounds/r{N}/verification-result.json` |
| 반려 사유·수정 요청 | `artifacts/rounds/r{N}/revision-request.md` |
| 최종 제안서·견적 포함 | `artifacts/final/proposal-quote.md` |
| 최종 제안서 HTML | `artifacts/final/proposal-quote.html` |
| 교차 검토 보고서 | `artifacts/final/cross-review-report.md` |
| 교차 검토 보고서 HTML | `artifacts/final/cross-review-report.html` |

## 검토 기준

확정한 체크리스트의 모든 항목에 원문 위치·판정 근거를 남기고, 견적과 예상 성과를 독립적으로 재계산합니다. 재계산은 [검산 스크립트](artifacts/scripts/README.md)를 평가 대상 초안의 값으로 실행하고 실행 근거를 해당 라운드 평가에 남깁니다. 통과 수는 Y인 항목 수/전체 항목 수로 기록합니다. 모든 항목을 충족하고 검산을 마친 문서만 최종본으로 확정합니다.

평가 기록에는 실제 사용 입력·양식·요구사항·체크리스트·초안의 문서명·경로와 평가 대상 라운드를 남깁니다. 최종본은 이번 작업에서 통과한 초안으로만 갱신합니다. 이번 작업이 반려·미완료라면 이전 최종본을 이번 통과 결과로 표시하지 않습니다. 수정 내역은 고객 본문과 분리합니다.

수정 후에는 같은 기준으로 재검사합니다. 예산·기간·업무 범위가 변경되면 영향받는 문서와 계산을 함께 갱신하고, 이전 기준과 검사 기록은 보존합니다.

## 최종 문서의 HTML

- [제안서 스타일](references/design/proposal-quote.html)과 [교차 검토 보고서 스타일](references/design/cross-review-report.html)에서 색상·글꼴·배치·표·다크/라이트 전환을 참고합니다.
- 내용과 섹션·표·카드 수는 최종 Markdown에 맞춥니다. 대괄호 자리표시자는 실제 내용으로 바꾸고, 판정은 `Y - 통과`·`N - 반려`로 표시합니다.
- 최종 HTML은 제안서와 교차 검토 보고서 2개만 만듭니다. 초안·평가 기록 등 근거 문서는 HTML로 만들거나 링크하지 않고 문서명·라운드·항목으로만 표시합니다.
- 두 HTML은 상대 링크로 연결합니다. 브라우저에서 모든 내부 링크의 대상 파일·구역을 확인하고, 깨진 링크·잘못된 이동을 수정하거나 불필요한 링크를 제거한 뒤 다시 확인합니다. 표시·테마 전환과 Markdown 내용도 대조합니다.

## 참고자료

- 요구사항: [양식](references/templates/requirements-template.md), [샘플](references/samples/requirements-sample.md)
- 체크리스트: [양식](references/templates/evaluation-checklist-template.md), [샘플](references/samples/evaluation-checklist-sample.md)
- 평가 기록: [양식](references/templates/evaluation-template.md), [샘플](references/samples/evaluation-sample.md)

- 제안·견적: [양식](references/templates/proposal-quote-template.md), [샘플](references/samples/proposal-quote-sample.md)
- 교차 검토 보고서: [양식](references/templates/cross-review-report-template.md), [샘플](references/samples/cross-review-report-sample.md)
