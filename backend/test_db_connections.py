import sys
sys.path.insert(0, '/home/vinay/Swaya.me/backend')

from persistence.database import SessionLocal
from sqlalchemy import text

db = SessionLocal()
try:
    # Test SHOW PROCESSLIST
    print("Testing SHOW PROCESSLIST...")
    result = db.execute(text("SHOW PROCESSLIST"))
    rows = result.fetchall()
    
    print(f"\nFound {len(rows)} database connections:")
    print("-" * 80)
    print(f"{'ID':<8} {'User':<16} {'Host':<25} {'DB':<20} {'Command':<12}")
    print("-" * 80)
    
    for row in rows[:10]:  # Show first 10
        print(f"{row[0]:<8} {row[1]:<16} {row[2]:<25} {str(row[3] or ''):<20} {row[4]:<12}")
    
    if len(rows) > 10:
        print(f"... and {len(rows) - 10} more")
    
    print("\n" + "=" * 80)
    print(f"✅ Total DB Connections: {len(rows)}")

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()

finally:
    db.close()
