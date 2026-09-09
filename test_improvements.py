import asyncio
import os
import sys
from database.db import init_db, get_db
from handlers.admin import set_maintenance_mode, get_maintenance_mode
from utils.email_sender import send_email, email_queue, email_worker

async def test_improvements():
    print("Testing Improvements...")
    
    # 1. Test DB Persistence for Maintenance Mode
    print("\n[1] Testing Maintenance Mode Persistence...")
    init_db()
    
    # Set to True
    set_maintenance_mode(True)
    if get_maintenance_mode() is True:
        print("✅ Maintenance Mode set to True (persisted).")
    else:
        print("❌ Failed to set Maintenance Mode to True.")

    # Set to False
    set_maintenance_mode(False)
    if get_maintenance_mode() is False:
        print("✅ Maintenance Mode set to False (persisted).")
    else:
        print("❌ Failed to set Maintenance Mode to False.")
        
    # 2. Test Email Sender Refactor
    print("\n[2] Testing Email Sender Refactor...")
    
    # Mock send_email_sync to avoid actual sending
    import utils.email_sender
    original_sync_send = utils.email_sender._send_email_sync
    
    mock_called = False
    def mock_send(*args, **kwargs):
        nonlocal mock_called
        mock_called = True
        print("✅ Mock email sent successfully.")
        return True
        
    utils.email_sender._send_email_sync = mock_send
    
    # Start worker task
    worker_task = asyncio.create_task(email_worker())
    
    # Send email
    # We need to wait a bit for worker to init queue
    await asyncio.sleep(0.1)
    
    success = send_email("test@example.com", "Test Subject", "Test Body", [])
    if success:
        print("✅ send_email returned True (enqueued).")
    else:
        print("❌ send_email returned False.")
        
    # Wait for worker to process
    await asyncio.sleep(0.5)
    
    if mock_called:
        print("✅ Email processed by worker.")
    else:
        print("❌ Email NOT processed by worker.")
        
    # Cleanup
    worker_task.cancel()
    try:
        await worker_task
    except asyncio.CancelledError:
        pass
    utils.email_sender._send_email_sync = original_sync_send

if __name__ == "__main__":
    asyncio.run(test_improvements())
