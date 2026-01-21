"""
Database initialization script to create roles and permissions.

Run this script after creating the database to set up initial roles and permissions.

Usage:
    python init_db.py
"""

import asyncio
from app.database import AsyncSessionLocal
from app.models.user import Role, Permission


async def init_db():
    """Initialize database with default roles and permissions."""
    
    async with AsyncSessionLocal() as session:
        print("Creating permissions...")
        
        # Create permissions
        permissions = [
            Permission(name="is_kalpass"),
            Permission(name="is_netra"),
            Permission(name="is_c2"),
        ]
        
        # Create a map for easy access
        perm_map = {p.name: p for p in permissions}
        
        session.add_all(permissions)
        await session.flush()
        
        print(f"Created {len(permissions)} permissions")
        
        print("Creating roles...")
        
        # Create SUPER_ADMIN role with all permissions
        super_admin_role = Role(name="SUPER_ADMIN")
        super_admin_role.permissions = permissions
        
        # Create ADMIN role with is_netra and is_c2
        admin_role = Role(name="ADMIN")
        admin_role.permissions = [
            perm_map["is_netra"],
            perm_map["is_c2"]
        ]
        
        # Create OPERATOR role with only is_netra
        operator_role = Role(name="OPERATOR")
        operator_role.permissions = [
            perm_map["is_netra"]
        ]
        
        session.add_all([super_admin_role, admin_role, operator_role])
        await session.commit()
        
        print("Created roles: SUPER_ADMIN, ADMIN, OPERATOR")
        print("\nRole permissions:")
        print(f"  - SUPER_ADMIN: {[p.name for p in super_admin_role.permissions]}")
        print(f"  - ADMIN: {[p.name for p in admin_role.permissions]}")
        print(f"  - OPERATOR: {[p.name for p in operator_role.permissions]}")
        print("\n✅ Database initialized successfully!")


if __name__ == "__main__":
    asyncio.run(init_db())
