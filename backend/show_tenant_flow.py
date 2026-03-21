import sys
sys.path.insert(0, '/home/vinay/Swaya.me/backend')

from persistence.database import SessionLocal
from persistence.models.core import Tenant, User

db = SessionLocal()
try:
    print("=" * 80)
    print("HOW TENANT ASSIGNMENT WORKS IN SWAYA.ME")
    print("=" * 80)
    
    print("\n📝 SCENARIO 1: New User Self-Registration")
    print("-" * 80)
    print("Registration Form:")
    print("  ├─ Tenant Name: 'Acme Corp'        ← User enters company name")
    print("  ├─ Email: john@acme.com")
    print("  ├─ Full Name: John Doe")
    print("  └─ Password: ********")
    print()
    print("Backend Creates:")
    print("  ├─ NEW Tenant (id=1, name='Acme Corp', tier='free')")
    print("  └─ NEW User (id=1, email='john@acme.com', tenant_id=1)")
    print()
    print("Result: John is the first user in 'Acme Corp' tenant")
    
    print("\n" + "=" * 80)
    print("\n👥 SCENARIO 2: Admin Creates User in User Management")
    print("-" * 80)
    print("Admin (john@acme.com from 'Acme Corp') creates a user:")
    print()
    print("User Form in Admin Panel:")
    print("  ├─ Email: jane@acme.com")
    print("  ├─ Full Name: Jane Smith")
    print("  ├─ Role: user")
    print("  └─ [NO TENANT FIELD - automatic!]")
    print()
    print("Backend Logic:")
    print("  ├─ Get current admin's tenant_id (from JWT token)")
    print("  ├─ Admin is from tenant_id=1 ('Acme Corp')")
    print("  └─ Create new user with tenant_id=1")
    print()
    print("Result: Jane is added to 'Acme Corp' tenant automatically")
    
    print("\n" + "=" * 80)
    print("\n🔍 YOUR CURRENT SITUATION")
    print("-" * 80)
    
    tenants = db.query(Tenant).all()
    
    for tenant in tenants:
        users = db.query(User).filter(User.tenant_id == tenant.id).all()
        print(f"\nTenant #{tenant.id}: '{tenant.name}' ({tenant.tier})")
        print(f"  Created: {tenant.created_at.strftime('%Y-%m-%d %H:%M')}")
        print(f"  Users ({len(users)}):")
        for user in users:
            print(f"    - {user.email} (role: {user.role.value})")
    
    print("\n" + "=" * 80)
    print("\n⚠️  ISSUE DETECTED: Duplicate Tenant Names")
    print("-" * 80)
    
    # Find duplicate names
    from collections import Counter
    tenant_names = [t.name for t in tenants]
    duplicates = {name: count for name, count in Counter(tenant_names).items() if count > 1}
    
    if duplicates:
        for name, count in duplicates.items():
            print(f"\n'{name}' appears {count} times:")
            matching_tenants = [t for t in tenants if t.name == name]
            for t in matching_tenants:
                user_count = db.query(User).filter(User.tenant_id == t.id).count()
                print(f"  - Tenant ID {t.id} (created: {t.created_at.strftime('%Y-%m-%d')}, {user_count} user)")
        
        print("\nRECOMMENDATION:")
        print("  - These are separate organizations with same name")
        print("  - Consider renaming one or merging if they're the same org")
    
    print("\n" + "=" * 80)
    print("\n✅ KEY TAKEAWAYS")
    print("-" * 80)
    print("1. Registration: User provides 'Tenant Name' → Creates NEW tenant")
    print("2. Admin Creates User: Automatically uses admin's tenant")
    print("3. Tenant Field in Export: Shows which org the user belongs to")
    print("4. No tenant selection needed: It's automatic based on context!")
    print("=" * 80)

finally:
    db.close()
