
import asyncio
import sys
import os
from unittest.mock import MagicMock, patch

# Add backend to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.schemas import AccountingStandard

# Mock the imports that might cause side effects or require full environment
with patch('core.progress.progress_tracker') as mock_tracker:
    with patch('api.routes.audit.audit_results', {}) as mock_results:
        from api.routes.audit import resume_audit, _run_audit_task

async def reproduce_issue():
    print("--- Simulating Audit Resume with Missing Standard ---")
    
    company_id = "test_company"
    audit_id = "test_audit"
    
    # Mock companies dictionary
    mock_companies = {
        "test_company": {
            "metadata": MagicMock(name="Test Company"),
            "data": {}
        }
    }
    
    # Mock progress tracker behavior
    from api.routes.audit import progress_tracker
    progress_tracker.has_checkpoint.return_value = True
    # Now including accounting_standard in checkpoint
    progress_tracker.get_checkpoint.return_value = {
        "phase": "testing", 
        "data": {},
        "accounting_standard": AccountingStandard.IFRS.value
    }
    progress_tracker.get_status.return_value = "paused"
    
    try:
        # Mock asyncio.create_task to intercept the _run_audit_task call
        with patch('asyncio.create_task') as mock_create_task:
            with patch('api.routes.company.companies', mock_companies):
                # We want to simulate that we STARTED with IFRS, but it was lost.
                # But currently, there is no place where we store "intent" other than audit_results or memory.
                # So if audit_results is empty, it defaults to GAAP.
                
                try:
                    response = await resume_audit(company_id, audit_id)
                except Exception as e:
                    print(f"ERROR calling resume_audit: {e}")
                    import traceback
                    traceback.print_exc()
                    return False
                
                # Extract the coroutine passed to create_task
                coro = mock_create_task.call_args[0][0]
                
                # Inspect the coroutine's arguments by looking at the closures or just knowing it's _run_audit_task
                # Since _run_audit_task is an async function, calling it returns a coroutine. 
                # We can't easily inspect arguments of a created coroutine object in a robust way across python versions
                # without inspecting cr_frame which is low level.
                
                # Better approach: Patch _run_audit_task directly to see how it was called.
                pass

        # Re-run with patched _run_audit_task
        with patch('api.routes.audit._run_audit_task', new_callable=MagicMock) as mock_run_task:
            mock_run_task.return_value = asyncio.Future()
            mock_run_task.return_value.set_result(None)
            
            with patch('api.routes.company.companies', mock_companies):
                 with patch('asyncio.create_task'):
                    try:
                        await resume_audit(company_id, audit_id)
                    except Exception as e:
                        print(f"ERROR calling resume_audit (2nd pass): {e}")
                        import traceback
                        traceback.print_exc()
                        return False
                    
                    # Check arguments
                    call_args = mock_run_task.call_args
                    if not call_args:
                         print("ERROR: _run_audit_task was not called")
                         return False

                    kwargs = call_args.kwargs
                    print(f"Resume called with accounting_standard: {kwargs.get('accounting_standard')}")
                    
                    if kwargs.get('accounting_standard') == AccountingStandard.IFRS:
                        print("reproduce_issue: SUCCESS - Correctly restored IFRS from checkpoint.")
                        return True
                    else:
                        print(f"reproduce_issue: FAILURE - Expected IFRS, got {kwargs.get('accounting_standard')}")
                        return False
    except Exception as e:
        print(f"CRITICAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        success = loop.run_until_complete(reproduce_issue())
        with open("verdict.txt", "w") as f:
            if success:
                f.write("SUCCESS: Audit standard restored correctly.\n")
                print("\nSUCCESS: Audit standard restored correctly.")
                exit(0)
            else:
                f.write("FAILURE: Audit standard was not restored.\n")
                print("\nFAILURE: Audit standard was not restored.")
                exit(1)
    except Exception as e:
        with open("verdict.txt", "w") as f:
            f.write(f"ERROR: {str(e)}\n")
        print(f"ERROR: {str(e)}")
        exit(1)
    finally:
        loop.close()
