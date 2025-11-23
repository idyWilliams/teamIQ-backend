from app.core.database import SessionLocal
from app.models.integration import IntegrationConnection
from app.models.project import Project
from app.models.project_resource import ProjectResource

def debug_integrations():
    db = SessionLocal()
    try:
        print("Querying IntegrationConnection table...")
        conns = db.query(IntegrationConnection).all()
        print(f"Found {len(conns)} connections.")
        for c in conns:
            print(f"ID: {c.id}, Provider: {c.provider}, Org: {c.organization_id}, Active: {c.is_active}")

        # Check specifically for ID 1
        conn1 = db.query(IntegrationConnection).filter_by(id=1).first()
        if conn1:
            print(f"\nConnection 1 found: {conn1.provider}, Active: {conn1.is_active}")
        else:
            print("\nConnection 1 NOT found.")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    debug_integrations()
