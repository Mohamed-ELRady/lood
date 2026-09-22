from app.models import DownloadRequest


def test_download_requires_rights_confirmation():
    try:
        DownloadRequest(
            url="https://youtube.com/watch?v=test",
            format_id="18",
            output_type="video",
            authorized=False,
        )
        assert False, "validation should fail"
    except ValueError as error:
        assert "allowed" in str(error)

