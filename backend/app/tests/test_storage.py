import io

import boto3
import pytest
from botocore.response import StreamingBody
from botocore.stub import Stubber

from app.integrations.storage import S3Storage


@pytest.fixture
def s3():
    client = boto3.client("s3", region_name="us-east-2", endpoint_url="https://s3.example.test",
                          aws_access_key_id="k", aws_secret_access_key="s")
    with Stubber(client) as stub:
        yield S3Storage("ic-uploads", client=client), stub


def test_put_get_delete(s3):
    store, stub = s3
    stub.add_response("put_object", {}, {"Bucket": "ic-uploads", "Key": "tryon/a.png", "Body": b"png"})
    stub.add_response("get_object", {"Body": StreamingBody(io.BytesIO(b"png"), 3)}, {"Bucket": "ic-uploads", "Key": "tryon/a.png"})
    stub.add_response("delete_object", {}, {"Bucket": "ic-uploads", "Key": "tryon/a.png"})
    store.put("tryon/a.png", b"png")
    assert store.get("tryon/a.png") == b"png"
    store.delete("tryon/a.png")
    stub.assert_no_pending_responses()


def test_missing_key_is_file_not_found(s3):
    store, stub = s3
    stub.add_client_error("get_object", service_error_code="NoSuchKey", http_status_code=404)
    with pytest.raises(FileNotFoundError):
        store.get("assessment-images/missing.jpg")


@pytest.mark.parametrize("key", ["", "/abs", "a/../b", ".."])
def test_rejects_bad_keys(s3, key):
    store, _ = s3
    with pytest.raises(ValueError):
        store.put(key, b"x")
