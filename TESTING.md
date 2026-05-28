# Acceptance Test Matrix (8 Operations)

| # | Operation | Type | Agent | HIL? | Example chat message |
|---|-----------|------|-------|------|----------------------|
| 1 | list_projects | READ | Query | No | What projects do I have? |
| 2 | list_tasks | READ | Query | No | Show tasks for the first project |
| 3 | get_task_details | READ | Query | No | Show details for the first task |
| 4 | list_project_members | READ | Query | No | Who are the members of the first project? |
| 5 | get_task_utilisation | READ | Query | No | Who has the most tasks in the first project? |
| 6 | create_task | WRITE | Action | **Yes** | Create a task called API Integration |
| 7 | update_task | WRITE | Action | **Yes** | Update task status to completed |
| 8 | delete_task | WRITE | Action | **Yes** | Delete task named API Integration |

## Run automated checks

```powershell
cd zoho-chatbot\backend
uvicorn main:app --host 127.0.0.1 --port 8000
python scripts/run_acceptance_tests.py YOUR_SESSION_ID
```

## HIL flow (6–8)

1. User sends write request → bot shows **Confirmation required**
2. User clicks **Yes, proceed** or **Cancel**
3. On Yes → action executes; on No → cancelled with no changes
