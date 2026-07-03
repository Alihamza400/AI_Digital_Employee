import sys
import time
import signal
from threading import Thread
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

print("=" * 70)
print("🔄 STARTING PERSONAL AI EMPLOYEE - BRONZE TIER")
print("=" * 70)
print("\nThis script implements the FileSystemWatcher for Hackathon 0.")
print("It watches the AI_Employee_Vault/Inbox/ folder and processes files.")
print("\n📋 Features:")
print("   • Event-driven file monitoring (no polling)")
print("   • Automatic binary file processing")
print("   • Rich metadata generation")
print("   • Automatic cleanup of source files")
print("   • Comprehensive logging")
print("\n🎯 Usage:")
print("   1. Run this script to start the watcher")
print("   2. Add files to AI_Employee_Vault/Inbox/")
print("   3. Check results in AI_Employee_Vault/Needs_Action/")
print("   4. View logs in watcher.log")
print("\n⚠️  Press Ctrl+C to stop the watcher gracefully")
print("=" * 70)

# Configure logging
import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler('watcher.log'), logging.StreamHandler()]
)

# Import our watcher module
sys.path.insert(0, str(Path.cwd()))
from src.watchers import FileSystemWatcher

def main():
    try:
        print(f"\n🚀 Starting FileSystemWatcher at {time.strftime('%H:%M:%S')}")
        
        # Initialize the watcher
        watcher = FileSystemWatcher('AI_Employee_Vault')
        
        # Start watching in a background thread
        watcher_thread = Thread(target=watcher.run, daemon=True)
        watcher_thread.start()
        
        print(f"✅ Watcher initialized successfully!")
        print(f"   📁 Watching directory: {watcher.inbox_path}")
        print(f"   📋 Output directory: {watcher.needs_action}")
        print(f"   🕒 Thread ID: {watcher_thread.ident}")
        print(f"   🔄 Thread daemon: {watcher_thread.daemon}")
        print()
        print(f"\n📁 Current folder structure:")
        print(f"   📁 AI_Employee_Vault/")
        inbox_files = len(list(Path('AI_Employee_Vault/Inbox').iterdir())) if Path('AI_Employee_Vault/Inbox').exists() else 0
        print(f"   ├── Inbox/ ({inbox_files} files)")
        needs_action_files = len(list(Path('AI_Employee_Vault/Needs_Action').iterdir())) if Path('AI_Employee_Vault/Needs_Action').exists() else 0
        print(f"   ├── Needs_Action/ ({needs_action_files} files)")
        print(f"   ├── In_Progress/")
        print(f"   └── Done/")

        print(f"\n🎯 Ready to process files!")
        print(f"   📤 Drop files into AI_Employee_Vault/Inbox/")
        print(f"   📥 Check results in AI_Employee_Vault/Needs_Action/")
        print(f"\n⚠️  Press Ctrl+C to stop the watcher")

        # Keep the main thread alive
        while watcher_thread.is_alive():
            time.sleep(0.1)
            
    except KeyboardInterrupt:
        print(f"\n🛑 Shutdown signal received at {time.strftime('%H:%M:%S')}")
        print("🧹 Cleaning up and exiting...")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
