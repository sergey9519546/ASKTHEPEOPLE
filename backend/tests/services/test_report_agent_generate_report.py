import pytest
from unittest.mock import MagicMock, patch

from app.services.report_agent import (
    ReportAgent,
    ReportStatus,
    ReportOutline,
    ReportSection,
)


@pytest.fixture
def mock_agent():
    # Setup standard agent mock without making real API calls
    with patch("app.services.report_agent.LLMClient"):
        with patch("app.services.report_agent.ZepToolsService"):
            agent = ReportAgent(
                graph_id="test_graph",
                simulation_id="test_sim",
                simulation_requirement="Test requirement",
            )
            # Prevent these from doing anything
            agent.report_logger = MagicMock()
            agent.console_logger = MagicMock()
            yield agent


class TestGenerateReport:
    @patch("app.services.report_agent.ReportManager")
    def test_generate_report_success(self, mock_report_manager, mock_agent):
        """Test successful full generation of report"""
        # Set up mocks
        mock_outline = ReportOutline(
            title="Test Title",
            summary="Test Summary",
            sections=[
                ReportSection(title="Section 1"),
                ReportSection(title="Section 2"),
            ],
        )

        # Mock agent methods
        mock_agent.plan_outline = MagicMock(return_value=mock_outline)
        mock_agent._generate_section_react = MagicMock(
            side_effect=["Content 1", "Content 2"]
        )

        # Mock ReportManager assemble
        mock_report_manager.assemble_full_report.return_value = "Full markdown content"

        # Mock progress callback
        mock_progress_callback = MagicMock()

        # We need to patch these specific logger classes that are instantiated locally in generate_report
        with (
            patch("app.services.report_agent.ReportLogger"),
            patch("app.services.report_agent.ReportConsoleLogger"),
        ):
            # Execute
            report = mock_agent.generate_report(
                progress_callback=mock_progress_callback, report_id="test_report_123"
            )

        # Assertions
        assert report.report_id == "test_report_123"
        assert report.status == ReportStatus.COMPLETED
        assert report.markdown_content == "Full markdown content"
        assert len(report.outline.sections) == 2

        # Check ReportManager calls
        mock_report_manager._ensure_report_folder.assert_called_once_with(
            "test_report_123"
        )
        assert (
            mock_report_manager.save_report.call_count >= 3
        )  # Init, Planning, Completed
        mock_report_manager.save_outline.assert_called_once()
        assert mock_report_manager.save_section.call_count == 2

        # Check progress callbacks
        assert mock_progress_callback.call_count > 0
        mock_progress_callback.assert_any_call(
            "completed", 100, "Report generation complete"
        )

        # Check method calls
        mock_agent.plan_outline.assert_called_once()
        assert mock_agent._generate_section_react.call_count == 2

    @patch("app.services.report_agent.ReportManager")
    def test_generate_report_no_report_id(self, mock_report_manager, mock_agent):
        """Test generating report when no report_id is provided generates one"""
        mock_outline = ReportOutline(title="Test", summary="Test", sections=[])
        mock_agent.plan_outline = MagicMock(return_value=mock_outline)

        with patch("uuid.uuid4") as mock_uuid:
            mock_uuid.return_value.hex = "1234567890123456"

            with (
                patch("app.services.report_agent.ReportLogger"),
                patch("app.services.report_agent.ReportConsoleLogger"),
            ):
                report = mock_agent.generate_report()

            assert report.report_id == "report_123456789012"

    @patch("app.services.report_agent.ReportManager")
    def test_generate_report_exception_handling(self, mock_report_manager, mock_agent):
        """Test that exceptions during generation are caught and status is FAILED"""
        # Set up an exception during planning
        mock_agent.plan_outline = MagicMock(side_effect=Exception("API Error"))

        # Both the stored error and the progress message are DEBUG-gated: with
        # DEBUG off they collapse to a bare "Report generation failed". Pin it
        # rather than inheriting whatever the ambient env happens to set.
        with patch("app.services.report_agent.Config") as mock_config:
            mock_config.DEBUG = True
            report = mock_agent.generate_report(report_id="test_error_report")

        # Assertions
        assert report.status == ReportStatus.FAILED
        assert "API Error" in report.error

        # Verify it still tried to save the failed report
        mock_report_manager.save_report.assert_called()
        mock_report_manager.update_progress.assert_called_with(
            "test_error_report",
            "failed",
            -1,
            "Report generation failed: API Error",
            completed_sections=[],
        )

    @patch("app.services.report_agent.ReportManager")
    def test_generate_report_no_progress_callback(
        self, mock_report_manager, mock_agent
    ):
        """Test generating report without a progress callback works fine"""
        mock_outline = ReportOutline(
            title="Test", summary="Test", sections=[ReportSection(title="Section 1")]
        )
        mock_agent.plan_outline = MagicMock(return_value=mock_outline)
        mock_agent._generate_section_react = MagicMock(return_value="Content")
        mock_report_manager.assemble_full_report.return_value = "Full report"

        with (
            patch("app.services.report_agent.ReportLogger"),
            patch("app.services.report_agent.ReportConsoleLogger"),
        ):
            report = mock_agent.generate_report(report_id="test_no_callback")

        assert report.status == ReportStatus.COMPLETED
        assert report.report_id == "test_no_callback"

    @patch("app.services.report_agent.ReportManager")
    def test_generate_report_handles_empty_outline(
        self, mock_report_manager, mock_agent
    ):
        """Test generating report when outline has no sections"""
        mock_outline = ReportOutline(
            title="Empty Outline", summary="No sections", sections=[]
        )
        mock_agent.plan_outline = MagicMock(return_value=mock_outline)
        mock_report_manager.assemble_full_report.return_value = "Full report empty"

        with (
            patch("app.services.report_agent.ReportLogger"),
            patch("app.services.report_agent.ReportConsoleLogger"),
        ):
            report = mock_agent.generate_report(report_id="test_empty_outline")

        assert report.status == ReportStatus.COMPLETED
        # _generate_section_react should not be called since there are no sections
        # _generate_section_react is not mocked with MagicMock in this specific test, but we know it would not be called

    @patch("app.services.report_agent.ReportManager")
    def test_generate_report_progress_callback_coverage(
        self, mock_report_manager, mock_agent
    ):
        """Test the inner progress callback lambda behavior"""
        mock_outline = ReportOutline(
            title="Test", summary="Test", sections=[ReportSection(title="Section 1")]
        )
        mock_agent.plan_outline = MagicMock(return_value=mock_outline)
        mock_agent._generate_section_react = MagicMock(return_value="Content")
        mock_report_manager.assemble_full_report.return_value = "Full report"

        # Track calls to the main progress callback
        callback_calls = []

        def mock_progress_callback(stage, prog, msg):
            callback_calls.append((stage, prog, msg))

        with (
            patch("app.services.report_agent.ReportLogger"),
            patch("app.services.report_agent.ReportConsoleLogger"),
        ):
            # Execute
            mock_agent.generate_report(
                progress_callback=mock_progress_callback, report_id="test_callback"
            )

        # The inner progress_callback passed to plan_outline should have been triggered
        # Let's manually trigger it to test the lambda coverage
        plan_outline_kwargs = mock_agent.plan_outline.call_args.kwargs
        inner_plan_callback = plan_outline_kwargs.get("progress_callback")
        if inner_plan_callback:
            inner_plan_callback("planning_inner", 50, "Inner plan message")

        # Manually trigger the generate section callback
        generate_kwargs = mock_agent._generate_section_react.call_args.kwargs
        inner_gen_callback = generate_kwargs.get("progress_callback")
        if inner_gen_callback:
            inner_gen_callback("generating_inner", 50, "Inner gen message")

        # Verify the custom callbacks successfully wrapped and called the main callback
        stages_called = [c[0] for c in callback_calls]
        assert "planning_inner" in stages_called
        assert "generating_inner" in stages_called

    @patch("app.services.report_agent.ReportManager")
    def test_generate_report_exception_in_save_report(
        self, mock_report_manager, mock_agent
    ):
        """Test that if saving a failed report throws an exception, it is caught and ignored"""
        mock_agent.plan_outline = MagicMock(side_effect=Exception("API Error"))

        # Make the save_report throw an exception ONLY when trying to save the failed state
        def side_effect(*args, **kwargs):
            if args and getattr(args[0], "status", None) == ReportStatus.FAILED:
                raise Exception("Save Failed")
            return None

        mock_report_manager.save_report.side_effect = side_effect

        # Execute (should not raise an exception)
        report = mock_agent.generate_report(report_id="test_error_report")

        # Assertions
        assert report.status == ReportStatus.FAILED
