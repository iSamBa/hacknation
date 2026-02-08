import logging
import uuid

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import UserProfile
from app.schemas.user import UserProfileUpdate

logger = logging.getLogger(__name__)

DEFAULT_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


async def geocode_address(address: str) -> tuple[float, float]:
    """Geocode an address string into (latitude, longitude) using Google Maps.

    Raises ValueError if the address cannot be geocoded.
    """
    from app.services.provider_search import _get_client

    client = _get_client()
    results = client.geocode(address)
    if not results:
        raise ValueError(f"Could not geocode address: {address!r}")
    location = results[0]["geometry"]["location"]
    return location["lat"], location["lng"]


async def get_or_create_default_user(db: AsyncSession) -> UserProfile:
    result = await db.execute(
        select(UserProfile).where(UserProfile.id == DEFAULT_USER_ID)
    )
    user = result.scalar_one_or_none()

    if user is not None:
        return user

    user = UserProfile(
        id=DEFAULT_USER_ID,
        name="Default User",
        address="",
        latitude=0.0,
        longitude=0.0,
    )
    db.add(user)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        result = await db.execute(
            select(UserProfile).where(UserProfile.id == DEFAULT_USER_ID)
        )
        user = result.scalar_one()

    await db.refresh(user)
    return user


async def update_user_profile(
    db: AsyncSession, user_id: uuid.UUID, data: UserProfileUpdate
) -> UserProfile:
    result = await db.execute(
        select(UserProfile).where(UserProfile.id == user_id)
    )
    user = result.scalar_one()

    update_data = data.model_dump(exclude_unset=True)

    # Auto-geocode when address is provided without explicit coordinates
    if update_data.get("address"):
        if "latitude" not in update_data or "longitude" not in update_data:
            try:
                lat, lng = await geocode_address(update_data["address"])
                update_data["latitude"] = lat
                update_data["longitude"] = lng
                logger.info(
                    "Geocoded address %r to (%s, %s)",
                    update_data["address"],
                    lat,
                    lng,
                )
            except ValueError:
                logger.warning(
                    "Failed to geocode address %r, coordinates unchanged",
                    update_data["address"],
                )

    for field, value in update_data.items():
        setattr(user, field, value)

    await db.commit()
    await db.refresh(user)
    return user
