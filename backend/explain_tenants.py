import sys
sys.path.insert(0, '/home/vinay/Swaya.me/backend')

from persistence.database import SessionLocal
from persistence.models.core import Tenant, User
from sqlalchemy import func

db = SessionLocal()
try:
    # Get all tenants
    tenants = db.query(Tenant).all()
    
    print("=" * 80)
    print("MULTI-TENANT SYSTEM OVERVIEW")
    print("=" * 80)
    
    print(f"\n📊 Total Tenants: {len(tenants)}\n")
    
    for tenant in tenants:
        # Count users in this tenant
        user_count = db.query(User).filter(User.tenant_id == tenant.id).count()
        
        print(f"Tenant ID: {tenant.id}")
        print(f"  Name:       {tenant.name}")
        print(f"  Tier:       {tenant.tier}")
        print(f"  Active:     {tenant.is_active}")
        print(f"  Users:      {user_count}")
        print(f"  Created:    {tenant.created_at.strftime('%Y-%m-%d')}")
        print()
    
    print("=" * 80)
    print("\nHow Multi-Tenancy Works in Swaya.me:")
    print("-" * 80)
    print("1. TENANT = Organization/Company")
    print("   - Each tenant has their own isolated data")
    print("   - Tenants have different subscription tiers (Free, Basic, Pro, Enterprise)")
    print()
    print("2. USERS belong to a TENANT")
    print("   - When you create a user, they're assigned to a tenant")
    print("   - Users can only see data from their own tenant")
    print()
    print("3. DATA ISOLATION")
    print("   - Quizzes, sessions, participants are all tenant-scoped")
    print("   - tenant_id column on all major tables")
    print()
    print("4. ROLES within a TENANT")
    print("   - super_admin: Platform-wide access (can see all tenants)")
    print("   - admin: Tenant admin (can manage their tenant)")
    print("   - user: Regular user (can create/run quizzes)")
    print("   - viewer: Read-only access")
    print()
    print("5. CURRENT SETUP")
    print(f"   - You have {len(tenants)} tenant(s) in the system")
    print(f"   - Each represents a separate organization using Swaya.me")
    print("=" * 80)

finally:
    db.close()
