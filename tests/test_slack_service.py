import pytest
from unittest.mock import MagicMock, patch
from app.services.slack_service import SlackService
from slack_sdk.errors import SlackApiError


@pytest.fixture
def slack_service():
    with patch("app.services.slack_service.WebClient") as MockClient:
        service = SlackService("xoxb-test-token", "C12345")
        yield service, MockClient.return_value


def test_send_report_text_only(slack_service):
    service, mock_client = slack_service
    summary = {"DONE": 10, "ERROR": 0}

    # 実行
    result = service.send_report(summary, csv_path=None)

    # 検証
    assert result is True
    mock_client.chat_postMessage.assert_called_once()
    args = mock_client.chat_postMessage.call_args[1]
    assert args["channel"] == "C12345"
    assert "処理合計: 10 件" in args["text"]


def test_send_report_with_csv(slack_service):
    service, mock_client = slack_service
    summary = {"DONE": 5}

    with patch("os.path.exists", return_value=True):
        # 実行
        result = service.send_report(summary, csv_path="dummy.csv")

    # 検証
    assert result is True
    mock_client.files_upload_v2.assert_called_once()
    args = mock_client.files_upload_v2.call_args[1]
    assert args["channel"] == "C12345"
    assert args["file"] == "dummy.csv"
    assert "RakutenBot Report" in args["title"]


def test_send_report_error_handling(slack_service):
    service, mock_client = slack_service
    mock_client.chat_postMessage.side_effect = SlackApiError(
        "error", {"error": "channel_not_found"}
    )
    summary = {"DONE": 0}

    # 実行
    result = service.send_report(summary)

    # 検証
    assert result is False
