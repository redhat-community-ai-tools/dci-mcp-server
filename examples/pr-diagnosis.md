# Diagnose PR 3191 failure with artifacts

**User**

Diagnose why PR 3191 failed - get test results from artifacts since main logs are likely sanitized

---

**Cursor**

I'll help you diagnose why PR 3191 failed by extracting test results from artifacts since the main logs are likely sanitized. Let me use the specialized tool for this purpose.

Now let me get additional diagnostic information about PR 3191 to provide more context:

## PR 3191 Failure Diagnosis

Based on the test artifacts analysis, here's what caused PR 3191 to fail:

### **Main Issue: E2E Test Container Failure**

The failure occurred in the **"Run multi-stage test e2e-tests"** step, which failed after running for about 26 minutes and 30 seconds.

### **Key Details:**

- **Build ID**: `1949479891216896000`
- **Job Status**: Failed  
- **Duration**: 2,509 seconds (~42 minutes total)
- **Container Exit Code**: 1 (Error)

### **Specific Failure Points:**

1. **Primary Failure**: The e2e-tests pod `e2e-tests-redhat-developer-rhdh` failed with container exit code 1
2. **Missing Logs**: Multiple containers had no previous logs available:
   - `prepare` container
   - `place-scripts` container  
   - `step-echo-goodbye` container
   - `step-echo-hello-world` container

### **Test Suite Breakdown:**

- **Total Tests**: 3
- **Failures**: 1  
- **Failed Test**: "Run multi-stage test e2e-tests" (took 2,389 seconds)
- **Successful Tests**:
  - "Find the input image ci-rhdh-e2e-runner-main and tag it into the pipeline" (0.7s)
  - "Import the release payload 'latest-e2e-tests' from an external source" (119.7s)

### **RBAC-Related Issues:**

The failure seems to be related to RBAC (Role-Based Access Control) testing, with logs mentioning:

- `showcase-rbac` namespace
- `hello-world-pipeline-run` pods
- `rhdh-rbac-developer-hub` deployment

### **Recommendation:**

The failure appears to be an infrastructure/environment issue rather than a code problem, as the test containers failed to start properly or maintain logs. This could indicate:

1. Resource constraints in the test environment
2. Kubernetes cluster issues
3. RBAC permission problems in the test namespace
4. Container image or deployment configuration issues

The missing logs suggest the containers may have crashed during initialization, preventing proper test execution.
