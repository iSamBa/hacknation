from unittest.mock import AsyncMock, MagicMock, patch

from app.core.deps import get_db


async def test_get_db_yields_session():
    mock_session = AsyncMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)

    with patch("app.core.deps.async_session", return_value=mock_session):
        gen = get_db()
        session = await gen.__anext__()
        assert session is mock_session
