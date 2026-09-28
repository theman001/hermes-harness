---
name: update-recon-summary
description: 정찰 결과를 고정 스키마(tech_stack/server/assets/discovered_endpoints/js_findings/waf_detected/notable_findings)로 기록·갱신한다. RAG 검색의 쿼리 입력이 된다.
version: 1.0.0
author: llm-abliteration project
license: MIT
platforms: [linux]
tags: [recon, redteam, bugbounty]
category: redteam
---

# Update Recon Summary

phase 시작 초반 recon 라운드들에서 채우고, 이후 라운드 중 새로 발견되는 게 있으면(예:
공격 중 숨겨진 관리자 페이지 발견) 그때그때 갱신한다 — 한 번 채우고 끝내는 게 아니다.
**`tech_stack`이 RAG 검색의 핵심 입력값**이라 이 필드가 틀리면 이후 모든 검색이 엉뚱한
카테고리를 가져온다 — 여러 신호(응답 헤더, 쿠키 이름, 에러 페이지 패턴)를 교차 확인해서
신뢰도를 높인 뒤 확정한다. 헤더+쿠키+에러페이지 중 최소 2개 이상 일치할 때만 확정하고,
불확실하면 `notable_findings`에 "추정, 미확정"으로 남긴 채 RAG 검색은 `web/general/`만
우선 적용한다(프레임워크 특화 카테고리는 오판 리스크가 있으니 보류).

## 동시쓰기 방지

`delegate_task` 자식이 이 Skill을 직접 호출하지 않는다 — 자식은 조사만 하고 부모에게
요약을 반환하며, 부모(A)가 위임 결과를 취합한 뒤에만 이 Skill을 호출한다(SOUL.md에
명시). 여러 자식이 같은 `recon_summary.json`에 동시에 쓰면 경합이 나기 때문이다.

## Schema

`journal/web/<project_id>/recon_summary.json`에 아래 스키마 그대로 저장(파일이 있으면
읽어서 병합 — 배열 필드는 append+dedup, 스칼라 필드는 새 값으로 덮어씀):

```json
{
  "tech_stack": ["php", "laravel"],
  "server": "nginx",
  "waf_detected": false,
  "assets": ["api.target.com", "staging.target.com"],
  "discovered_endpoints": ["/api/v1/users", "/.env", "/actuator/health"],
  "js_findings": ["/static/app.js 안에 내부 API 키 패턴 발견 — 검증 필요"],
  "notable_findings": ["legacy /admin-old 엔드포인트 노출, 인증 없음"],
  "updated_at": "2026-09-22T14:03:00Z"
}
```

| 필드 | 채우는 시점 |
|---|---|
| `tech_stack` | httpx `-tech-detect` 결과를 1차 소스로, 헤더/쿠키/에러페이지로 교차검증 후 확정 |
| `server` | 응답 헤더의 `Server` 값 |
| `waf_detected` | 요청 패턴에 따라 응답이 달라지거나 특정 벤더 시그니처가 보이면 true |
| `assets` | subfinder/crt.sh/gau 등 자산 발굴 결과 |
| `discovered_endpoints` | ffuf/알려진 프레임워크 기본경로 확인/브라우저 정찰로 찾은 경로 |
| `js_findings` | JS 파일에서 발견한 API 엔드포인트/키 패턴 |
| `notable_findings` | 위 필드들에 안 맞는 특이사항(그 자체로 공격 단서가 되는 것) |

## 저장 위치

`journal/web/<project_id>/recon_summary.json` — journal과 같은 project 레벨 폴더, phase
경계와 무관하게 영속.
