from sqlalchemy import Float, Integer, String, inspect

from app.models.provider import Provider


def test_provider_tablename():
    assert Provider.__tablename__ == "providers"


def test_provider_has_all_fields():
    mapper = inspect(Provider)
    expected_fields = [
        "id",
        "created_at",
        "updated_at",
        "place_id",
        "name",
        "address",
        "latitude",
        "longitude",
        "phone",
        "rating",
        "review_count",
        "is_open",
        "cached_at",
    ]
    for field in expected_fields:
        assert field in mapper.columns, f"Missing field: {field}"


def test_provider_place_id_unique_and_indexed():
    mapper = inspect(Provider)
    col = mapper.columns["place_id"]
    assert col.unique is True
    assert col.index is True


def test_provider_string_columns():
    mapper = inspect(Provider)
    string_fields = {"place_id": 255, "name": 255, "address": 500, "phone": 50}
    for field, length in string_fields.items():
        col = mapper.columns[field]
        assert isinstance(col.type, String)
        assert col.type.length == length


def test_provider_float_columns():
    mapper = inspect(Provider)
    for field in ["latitude", "longitude", "rating"]:
        col = mapper.columns[field]
        assert isinstance(col.type, Float)


def test_provider_review_count_is_integer():
    mapper = inspect(Provider)
    col = mapper.columns["review_count"]
    assert isinstance(col.type, Integer)


def test_provider_nullable_fields():
    mapper = inspect(Provider)
    assert mapper.columns["phone"].nullable is True
    assert mapper.columns["is_open"].nullable is True


def test_provider_cached_at_has_server_default():
    mapper = inspect(Provider)
    assert mapper.columns["cached_at"].server_default is not None


def test_provider_review_count_has_server_default():
    mapper = inspect(Provider)
    assert mapper.columns["review_count"].server_default is not None
