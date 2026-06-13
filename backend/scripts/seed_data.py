"""
Database seeding script
Seeds initial data for development and testing
"""
import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from sqlalchemy.orm import Session
from persistence.database import SessionLocal, engine, Base
from persistence.models.core import Tenant, User, TierConfiguration, TierEnum, UserRole
from persistence.models.quiz import Quiz, Question, QuizSession, Participant, Answer
from core.security.password import hash_password


def create_tables():
    """Create all tables"""
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("✓ Tables created")


def seed_tier_configurations(db: Session):
    """Seed tier configurations"""
    print("Seeding tier configurations...")
    
    tiers = [
        TierConfiguration(
            tier=TierEnum.FREE,
            max_participants=50,
            max_questions=10,
            max_concurrent_events=1,
            features=None
        ),
        TierConfiguration(
            tier=TierEnum.PRO,
            max_participants=1000,
            max_questions=100,
            max_concurrent_events=5,
            features=None
        ),
        TierConfiguration(
            tier=TierEnum.ENTERPRISE,
            max_participants=10000,
            max_questions=1000,
            max_concurrent_events=50,
            features=None
        )
    ]
    
    for tier_config in tiers:
        existing = db.query(TierConfiguration).filter(
            TierConfiguration.tier == tier_config.tier
        ).first()
        
        if not existing:
            db.add(tier_config)
            print(f"   Added tier: {tier_config.tier.value}")
    
    db.commit()
    print("✓ Tier configurations seeded")


def seed_demo_data(db: Session):
    """Seed demo tenant and user for development"""
    print("Seeding demo data...")
    
    # Check if demo tenant exists
    demo_tenant = db.query(Tenant).filter(Tenant.slug == "demo").first()
    if demo_tenant:
        print("   Demo data already exists")
        return
    
    # Create demo tenant
    tenant = Tenant(
        name="Demo Organization",
        slug="demo",
        tier=TierEnum.PRO,
        is_active=True
    )
    db.add(tenant)
    db.flush()
    
    # Create demo user
    user = User(
        tenant_id=tenant.id,
        email="demo@swaya.me",
        hashed_password=hash_password("Demo1234"),
        full_name="Demo User",
        is_active=True,
        is_email_verified=True,
        role=UserRole.super_admin
    )
    db.add(user)
    db.commit()
    
    print("   Created demo tenant: demo")
    print("   Created demo user: demo@swaya.me / Demo1234")
    print("✓ Demo data seeded")


def main():
    """Main seeding function"""
    print("\n🌱 Database Seeding Script\n")
    
    # Create tables
    create_tables()
    
    # Create session
    db = SessionLocal()
    
    try:
        # Seed tier configurations
        seed_tier_configurations(db)
        
        # Seed demo data
        seed_demo_data(db)
        
        print("\n✅ Database seeding completed successfully!\n")
        
    except Exception as e:
        print(f"\n❌ Error during seeding: {str(e)}\n")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
