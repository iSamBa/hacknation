from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.user import UserProfile
from app.schemas.user import UserProfileUpdate
from app.services.user_service import geocode_address, update_user_profile


class TestGeocodeAddress:
    @pytest.mark.asyncio
    @patch("app.services.provider_search._get_client")
    async def test_returns_lat_lng(self, mock_get_client):
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.geocode.return_value = [
            {"geometry": {"location": {"lat": 33.5731, "lng": -7.5898}}}
        ]

        lat, lng = await geocode_address("Casablanca, Morocco")

        assert lat == 33.5731
        assert lng == -7.5898
        mock_client.geocode.assert_called_once_with("Casablanca, Morocco")

    @pytest.mark.asyncio
    @patch("app.services.provider_search._get_client")
    async def test_raises_on_empty_results(self, mock_get_client):
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.geocode.return_value = []

        with pytest.raises(ValueError, match="Could not geocode"):
            await geocode_address("nonexistent place xyz")


class TestUpdateUserProfileGeocode:
    def _make_mock_db(self, user):
        mock_db = AsyncMock()
        result = MagicMock()
        result.scalar_one.return_value = user
        mock_db.execute.return_value = result
        return mock_db

    def _make_user(self, **overrides):
        defaults = {
            "latitude": 0.0,
            "longitude": 0.0,
            "address": "",
        }
        defaults.update(overrides)
        user = MagicMock(spec=UserProfile)
        for k, v in defaults.items():
            setattr(user, k, v)
        return user

    @pytest.mark.asyncio
    @patch("app.services.user_service.geocode_address")
    async def test_geocodes_when_address_set_without_coords(
        self, mock_geocode
    ):
        mock_geocode.return_value = (33.5731, -7.5898)
        user = self._make_user()
        mock_db = self._make_mock_db(user)

        data = UserProfileUpdate(address="Casablanca, Morocco")
        await update_user_profile(mock_db, user.id, data)

        mock_geocode.assert_awaited_once_with("Casablanca, Morocco")
        assert user.latitude == 33.5731
        assert user.longitude == -7.5898

    @pytest.mark.asyncio
    @patch("app.services.user_service.geocode_address")
    async def test_skips_geocode_when_coords_provided(self, mock_geocode):
        user = self._make_user()
        mock_db = self._make_mock_db(user)

        data = UserProfileUpdate(
            address="Casablanca", latitude=34.0, longitude=-7.0
        )
        await update_user_profile(mock_db, user.id, data)

        mock_geocode.assert_not_awaited()
        assert user.latitude == 34.0
        assert user.longitude == -7.0

    @pytest.mark.asyncio
    @patch("app.services.user_service.geocode_address")
    async def test_skips_geocode_when_no_address(self, mock_geocode):
        user = self._make_user()
        mock_db = self._make_mock_db(user)

        data = UserProfileUpdate(name="New Name")
        await update_user_profile(mock_db, user.id, data)

        mock_geocode.assert_not_awaited()

    @pytest.mark.asyncio
    @patch("app.services.user_service.geocode_address")
    async def test_geocode_failure_does_not_crash(self, mock_geocode):
        mock_geocode.side_effect = ValueError("Could not geocode")
        user = self._make_user()
        mock_db = self._make_mock_db(user)

        data = UserProfileUpdate(address="bad address xyz")
        await update_user_profile(mock_db, user.id, data)

        # Address still updated, coords unchanged
        assert user.address == "bad address xyz"
        assert user.latitude == 0.0
        assert user.longitude == 0.0
