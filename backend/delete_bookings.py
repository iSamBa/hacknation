#!/usr/bin/env python3.11
"""Delete all bookings from the database."""
import asyncio
from app.core.database import async_session
from sqlalchemy import text


async def delete_all_bookings():
    """Delete all bookings and related records."""
    async with async_session() as db:
        # Delete in correct order to avoid foreign key constraints
        result1 = await db.execute(text("DELETE FROM call_results"))
        result2 = await db.execute(text("DELETE FROM booking_providers"))
        result3 = await db.execute(text("DELETE FROM bookings"))
        await db.commit()

        print("✅ All bookings deleted successfully!")
        print(f"   - {result1.rowcount} call results deleted")
        print(f"   - {result2.rowcount} booking providers deleted")
        print(f"   - {result3.rowcount} bookings deleted")


if __name__ == "__main__":
    asyncio.run(delete_all_bookings())
