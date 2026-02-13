#!/usr/bin/env python3
"""
Database Health Check - Validates data integrity and identifies issues
Run before each deployment or when troubleshooting

Usage:
    python backend/scripts/db_health_check.py
"""

import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.orm import Session
from sqlalchemy import text
from persistence.database import SessionLocal, engine
from persistence.models.core import Tenant, User
from persistence.models.quiz import Quiz, QuizSession, Participant, Answer


def check_foreign_key_integrity(db: Session) -> dict:
    """Check FK relationships are valid"""
    results = {}
    
    print("\n📋 Checking Foreign Key Integrity...")
    
    # Check: Users have valid tenants
    orphan_users = db.query(User).where(
        ~User.tenant_id.in_(db.query(Tenant.id))
    ).count()
    results['orphan_users'] = orphan_users
    if orphan_users == 0:
        print("   ✅ All users have valid tenants")
    else:
        print(f"   ⚠️  {orphan_users} users have invalid tenant_id")
    
    # Check: Quizzes have valid events
    try:
        orphan_quizzes = db.execute(text(
            "SELECT COUNT(*) FROM quizzes q "
            "WHERE NOT EXISTS (SELECT 1 FROM events e WHERE e.id = q.event_id)"
        )).scalar()
        results['orphan_quizzes'] = orphan_quizzes
        if orphan_quizzes == 0:
            print("   ✅ All quizzes have valid events")
        else:
            print(f"   ⚠️  {orphan_quizzes} quizzes have invalid event_id")
    except Exception as e:
        print(f"   ❌ Error checking quizzes: {e}")
        results['orphan_quizzes_error'] = str(e)
    
    # Check: Sessions have valid quizzes
    try:
        orphan_sessions = db.execute(text(
            "SELECT COUNT(*) FROM quiz_sessions qs "
            "WHERE NOT EXISTS (SELECT 1 FROM quizzes q WHERE q.id = qs.quiz_id)"
        )).scalar()
        results['orphan_sessions'] = orphan_sessions
        if orphan_sessions == 0:
            print("   ✅ All sessions have valid quizzes")
        else:
            print(f"   ⚠️  {orphan_sessions} sessions have invalid quiz_id")
    except Exception as e:
        print(f"   ❌ Error checking sessions: {e}")
        results['orphan_sessions_error'] = str(e)
    
    return results


def check_active_status(db: Session) -> dict:
    """Check active status consistency"""
    results = {}
    
    print("\n📋 Checking Active Status Consistency...")
    
    # Check: Active users with inactive tenants
    try:
        inactive_tenants = db.execute(text(
            "SELECT COUNT(*) FROM users u "
            "JOIN tenants t ON u.tenant_id = t.id "
            "WHERE u.is_active = 1 AND t.is_active = 0"
        )).scalar()
        results['active_users_inactive_tenant'] = inactive_tenants
        if inactive_tenants == 0:
            print("   ✅ No active users with inactive tenants")
        else:
            print(f"   ⚠️  {inactive_tenants} active users have inactive tenants")
    except Exception as e:
        print(f"   ❌ Error checking user/tenant consistency: {e}")
    
    # Count active entities
    active_users = db.query(User).filter(User.is_active == True).count()
    active_tenants = db.query(Tenant).filter(Tenant.is_active == True).count()
    
    print(f"   ℹ️  Active users: {active_users}")
    print(f"   ℹ️  Active tenants: {active_tenants}")
    
    results['active_users'] = active_users
    results['active_tenants'] = active_tenants
    
    return results


def check_critical_data(db: Session) -> dict:
    """Check critical data exists"""
    results = {}
    
    print("\n📋 Checking Critical Data...")
    
    # Check: Demo user exists
    demo_user = db.query(User).filter(User.email == "demo@swaya.me").first()
    if demo_user:
        print(f"   ✅ Demo user exists (ID: {demo_user.id})")
        results['demo_user_exists'] = True
        
        # Check: Demo tenant exists
        demo_tenant = db.query(Tenant).filter(Tenant.id == demo_user.tenant_id).first()
        if demo_tenant:
            print(f"   ✅ Demo tenant exists (ID: {demo_tenant.id}, Tier: {demo_tenant.tier})")
            results['demo_tenant_exists'] = True
            
            # Check: Demo tenant is active
            if demo_tenant.is_active:
                print("   ✅ Demo tenant is active")
                results['demo_tenant_active'] = True
            else:
                print("   ⚠️  Demo tenant is INACTIVE")
                results['demo_tenant_active'] = False
        else:
            print("   ❌ Demo tenant not found!")
            results['demo_tenant_exists'] = False
    else:
        print("   ❌ Demo user NOT FOUND!")
        results['demo_user_exists'] = False
    
    # Count total data
    total_users = db.query(User).count()
    total_tenants = db.query(Tenant).count()
    total_quizzes = db.query(Quiz).count()
    
    print(f"\n   ℹ️  Total users: {total_users}")
    print(f"   ℹ️  Total tenants: {total_tenants}")
    print(f"   ℹ️  Total quizzes: {total_quizzes}")
    
    results['total_users'] = total_users
    results['total_tenants'] = total_tenants
    results['total_quizzes'] = total_quizzes
    
    return results


def check_indexes(db: Session) -> dict:
    """Check critical indexes exist"""
    results = {}
    
    print("\n📋 Checking Database Indexes...")
    
    # Get all indexes
    try:
        inspector = text(
            "SELECT DISTINCT TABLE_NAME, INDEX_NAME "
            "FROM INFORMATION_SCHEMA.STATISTICS "
            "WHERE TABLE_SCHEMA = DATABASE()"
        )
        indexes = db.execute(inspector).fetchall()
        print(f"   ℹ️  Found {len(indexes)} indexes")
        results['index_count'] = len(indexes)
    except Exception as e:
        print(f"   ❌ Error checking indexes: {e}")
    
    return results


def main():
    """Run all health checks"""
    db = SessionLocal()
    
    try:
        print("=" * 60)
        print("🏥 Swaya.me Database Health Check")
        print("=" * 60)
        
        all_results = {}
        
        all_results['fk_integrity'] = check_foreign_key_integrity(db)
        all_results['active_status'] = check_active_status(db)
        all_results['critical_data'] = check_critical_data(db)
        all_results['indexes'] = check_indexes(db)
        
        # Summary
        print("\n" + "=" * 60)
        print("📊 Summary")
        print("=" * 60)
        
        issues_found = False
        
        # Check for critical issues
        if all_results['fk_integrity'].get('orphan_users', 0) > 0:
            print("❌ CRITICAL: Orphan users found!")
            issues_found = True
        
        if all_results['fk_integrity'].get('orphan_quizzes', 0) > 0:
            print("❌ CRITICAL: Orphan quizzes found!")
            issues_found = True
        
        if not all_results['critical_data'].get('demo_user_exists', False):
            print("⚠️  WARNING: Demo user not found - run: python scripts/seed_data.py")
            issues_found = True
        
        if not all_results['critical_data'].get('demo_tenant_active', False):
            print("⚠️  WARNING: Demo tenant is inactive")
            issues_found = True
        
        if not issues_found:
            print("✅ No critical issues found!")
        
        print("\n💡 Recommendation:")
        if all_results['critical_data'].get('total_users', 0) == 0:
            print("   Run: python scripts/seed_data.py")
        else:
            print("   Database appears healthy. No action needed.")
        
        print("=" * 60)
        
        db.close()
        return 0 if not issues_found else 1
        
    except Exception as e:
        print(f"\n❌ Health check failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())

