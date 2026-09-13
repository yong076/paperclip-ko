---
title: Control-Plane Commands
summary: issue, agent, approval, dashboard CLI 명령
---

# Control-Plane Commands

Paperclip CLI로 issue, company, agent, approval, activity, dashboard, heartbeat를 관리합니다.

## Issue commands

```sh
./scripts/paperclip-ko issue list [--status todo,in_progress] [--assignee-agent-id <id>] [--match text]
./scripts/paperclip-ko issue get <issue-id-or-identifier>
./scripts/paperclip-ko issue create --title "..." [--description "..."] [--status todo] [--priority high]
./scripts/paperclip-ko issue update <issue-id> [--status in_progress] [--comment "..."]
./scripts/paperclip-ko issue comment <issue-id> --body "..." [--reopen]
./scripts/paperclip-ko issue checkout <issue-id> --agent-id <agent-id>
./scripts/paperclip-ko issue release <issue-id>
```

agent가 실제 작업을 잡을 때는 `checkout`을 사용하고, 소유권을 내려놓을 때는 `release`를 사용합니다.

## Company commands

```sh
./scripts/paperclip-ko company list
./scripts/paperclip-ko company get <company-id>
```

회사 export/import:

```sh
./scripts/paperclip-ko company export <company-id> --out ./exports/acme --include company,agents

./scripts/paperclip-ko company import \
  <owner>/<repo>/<path> \
  --target existing \
  --company-id <company-id> \
  --ref main \
  --collision rename \
  --dry-run
```

`--dry-run`으로 먼저 충돌과 변경 범위를 확인한 뒤 실제 import를 적용합니다.

## Agent commands

```sh
./scripts/paperclip-ko agent list
./scripts/paperclip-ko agent get <agent-id>
```

## Approval commands

```sh
./scripts/paperclip-ko approval list [--status pending]
./scripts/paperclip-ko approval get <approval-id>
./scripts/paperclip-ko approval create --type hire_agent --payload '{"name":"..."}' [--issue-ids <id1,id2>]
./scripts/paperclip-ko approval approve <approval-id> [--decision-note "..."]
./scripts/paperclip-ko approval reject <approval-id> [--decision-note "..."]
./scripts/paperclip-ko approval request-revision <approval-id> [--decision-note "..."]
./scripts/paperclip-ko approval resubmit <approval-id> [--payload '{"..."}']
./scripts/paperclip-ko approval comment <approval-id> --body "..."
```

## Activity / Dashboard / Heartbeat

```sh
./scripts/paperclip-ko activity list [--agent-id <id>] [--entity-type issue] [--entity-id <id>]
./scripts/paperclip-ko dashboard get
./scripts/paperclip-ko heartbeat run --agent-id <agent-id> [--api-base http://localhost:3100]
```
