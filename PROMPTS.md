# DCI MCP Tool Prompts

This document contains a comprehensive collection of prompts for the DCI MCP tool, organized by category and use case.

## 🚀 **Quick Start Prompts**

### **Basic Exploration:**

```
List all DCI teams
```

```
Show me the last 10 DCI jobs from any team
```

```
What's the current status of DCI jobs for the MyTeam team?
```

### **Deep Dive Analysis:**
```
Get detailed information about the last failed DCI job including logs and artifacts
```

```
Show me all jobs for a specific team with their status and timing information
```

```
Find DCI jobs that match specific criteria (team, status, job type, time period)
```

## 🔍 **Team & Organization Analysis**

```
What are the names of all DCI teams and how many jobs does each team have?
```

```
Show me the teams with the most active DCI jobs (running status) in the last 7 days
```

```
Which team has the highest success rate for their DCI jobs?
```

## 📊 **Job Performance & Analytics**

```
What is the status breakdown of all DCI jobs for the MyTeam team?
```

```
Show me the last 10 failed DCI jobs from any team and their error details
```

```
Which DCI job names have the highest failure rate across all teams?
```

```
What are the most recent successful DCI jobs from the MyTeam team?
```

## 🎯 **Specific Team Deep Dives**

```
Get the status of the last DCI job with a daily tag from the MyTeam team on the OCP-4.20 topic
```

```
Show me all DCI jobs for the MyTeam team that are currently running
```

```
What are the different DCI job names that the MyTeam team runs?
```

## 📈 **Trend Analysis & Monitoring**

```
Show me DCI jobs that have been running for more than 24 hours
```

```
What are the most common DCI job names across all teams?
```

```
Show me the DCI job status trends for the last 30 days
```

## 🔧 **Component & Pipeline Analysis**

```
List all DCI components and show which ones are most frequently used in jobs
```

```
What DCI pipelines are associated with the MyTeam team's jobs?
```

```
Show me the DCI components used in failed jobs vs successful jobs
```

## 📁 **File & Artifact Analysis**

```
Download the logs from the last failed DCI job for the MyTeam team
```

```
Show me the artifacts from the most recent successful acm-hub DCI job
```

```
What files are available for the latest DCI job from the MyTeam team?
```

## 🔍 **Advanced Filtering & Search**

```
Find all DCI jobs with the 'daily' tag that failed in the last week
```

```
Show me DCI jobs that contain 'ptp' in the name and are currently running
```

```
List all jobs for teams that have 'ran' in their name
```

## 📋 **Summary & Overview Prompts**

```
Give me a comprehensive overview of DCI activity: total teams, total jobs, success rates, and most active teams
```

```
Show me a summary of all DCI topics and how many jobs are associated with each
```

```
What's the current state of DCI: how many teams, how many active jobs, and what are the most common job types?
```

## 🔍 **Troubleshooting & Debugging**

```
Find all jobs that failed with 'timeout' errors in the last 24 hours
```

```
Show me the logs from the most recent failed DCI job to help debug the issue
```

```
What are the common failure patterns across different DCI job names?
```

## 📊 **Reporting & Metrics**

```
Generate a weekly report for DCI jobs: total jobs, success rate, top performing teams, and most common job names
```

```
Show me the DCI job completion trends for the MyTeam team over the last month
```

```
What are the busiest times for DCI job execution across all teams?
```

## 🎯 **Best Prompts for Different Use Cases**

### **For Team Leads:**

```
What's the current status of my team's DCI jobs and what are the main issues we need to address?
```

### **For DevOps Engineers:**

```
Show me the logs from the last 3 failed DCI jobs to identify common failure patterns
```

### **For Management:**

```
Give me a high-level overview of DCI usage: team activity, success rates, and resource utilization
```

### **For Debugging:**

```
Find the most recent failed DCI job with detailed logs and error information
```

## 📝 **Usage Tips**

- **Combine filters**: Use team names, job status, and time periods together
- **Use pagination**: For large datasets, the tool automatically handles pagination
- **Leverage file access**: Download logs and artifacts for detailed analysis
- **Monitor trends**: Ask for historical data to identify patterns
- **Focus on specific teams**: Target analysis to particular teams or job types

## 🔧 **Advanced Features**

The DCI MCP tool supports:
- **Automatic pagination** for large datasets
- **File downloads** for logs and artifacts
- **Flexible filtering** by team, status, job type, and time
- **Comprehensive job metadata** including timing, status, and associated files
- **Real-time status updates** for monitoring active jobs 