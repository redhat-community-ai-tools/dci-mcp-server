"""MCP tools for log retrieval and processing."""

from fastmcp import FastMCP

from ..services.dci_log_service import DCILogService


def register_log_tools(mcp: FastMCP) -> None:
    """Register log-related tools with the MCP server."""

    @mcp.tool()
    async def get_dci_job_logs(job_id: str) -> str:
        """Get the logs for a specific DCI job ID.

        Args:
            job_id: The DCI job ID to get logs for

        Returns:
            Dictionary containing the job logs or error information
        """
        try:
            dci_log_service = DCILogService()
            result = await dci_log_service.get_job_logs(job_id)

            # Convert LogResult to dictionary for MCP response
            response = {
                "build_id": result.build_id,
                "job_name": result.job_name,
                "logs": result.logs,
                "artifacts_url": result.artifacts_url,
                "log_url_used": result.log_url_used,
            }

            if result.error:
                response["error"] = result.error

            return str(response)

        except Exception as e:
            return str({"error": f"Failed to fetch DCI job logs: {str(e)}"})

    @mcp.tool()
    async def get_dci_job_artifacts(job_id: str) -> str:
        """Get artifacts for a specific DCI job.

        Args:
            job_id: The DCI job ID to get artifacts for

        Returns:
            Dictionary containing artifact information
        """
        try:
            dci_log_service = DCILogService()
            result = await dci_log_service.get_job_artifacts(job_id)
            return str(result)

        except Exception as e:
            return str({"error": f"Failed to fetch DCI job artifacts: {str(e)}"})
