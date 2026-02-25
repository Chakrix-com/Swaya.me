import sys
sys.path.insert(0, '/home/vinay/Swaya.me/backend')

from persistence.database import SessionLocal
from persistence.models.core import Tenant, User

db = SessionLocal()
try:
    print("=" * 80)
    print("SAINT JOHN'S ACADEMY (SJA) - CURRENT SITUATION")
    print("=" * 80)
    
    # Get SJA tenants
    sja_tenants = db.query(Tenant).filter(Tenant.name == 'SJA').all()
    
    print(f"\nFound {len(sja_tenants)} tenant(s) named 'SJA'\n")
    
    for tenant in sja_tenants:
        users = db.query(User).filter(User.tenant_id == tenant.id).all()
        
        print(f"Tenant #{tenant.id}: SJA")
        print(f"  Created: {tenant.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"  Tier: {tenant.tier}")
        print(f"  Users ({len(users)}):")
        
        for user in users:
            print(f"    - {user.email}")
            print(f"      Role: {user.role.value}")
            print(f"      Active: {user.is_active}")
            print(f"      Login Count: {user.login_count}")
            print(f"      Created: {user.created_at.strftime('%Y-%m-%d %H:%M')}")
        print()
    
    print("=" * 80)
    print("❌ THE PROBLEM:")
    print("-" * 80)
    print("• Student (5012) registered first → became 'user' role")
    print("• Student (5588) registered separately → created duplicate tenant")
    print("• NO faculty member has admin access yet!")
    print()
    print("⚠️  WHAT THIS MEANS:")
    print("-" * 80)
    print("• Students CANNOT create other users (not admin)")
    print("• Students CANNOT manage quizzes for the organization")
    print("• If faculty joins, they'd have 'user' role too (same as students)")
    print("• No one can promote others to admin!")
    print()
    print("=" * 80)
    print("✅ SOLUTION OPTIONS:")
    print("-" * 80)
    print()
    print("Option 1: SUPER ADMIN PROMOTES FACULTY TO ADMIN")
    print("  • You (super_admin) can edit any user's role")
    print("  • When faculty joins, promote them to 'admin'")
    print("  • Then demote students back to 'user' or 'viewer'")
    print()
    print("Option 2: ADD INVITE CODE SYSTEM (Better long-term)")
    print("  • Create 'organization invite codes'")
    print("  • Faculty gets special 'admin invite code'")
    print("  • Students join with regular code")
    print("  • Auto-assigns correct role based on invite type")
    print()
    print("Option 3: ROLE TRANSFER FEATURE")
    print("  • Allow 'user' to request admin promotion")
    print("  • Super admin approves")
    print("  • Original user optionally demoted")
    print()
    print("=" * 80)
    print("\n🎯 IMMEDIATE FIX (Option 1):")
    print("-" * 80)
    print("1. Ask faculty to register normally")
    print("2. You (super_admin) go to User Management")
    print("3. Edit the faculty user → Change role to 'admin'")
    print("4. Merge or delete duplicate SJA tenant")
    print("5. Faculty can now manage their organization")
    print("=" * 80)

finally:
    db.close()
