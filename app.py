import json
import os
from typing import Any, Dict
from kubernetes import client, config
from mcp.server.fastmcp import FastMCP

# Initialize FastMCP server
mcp = FastMCP("kubernetes-mcp")

# Load Kubernetes configuration
try:
    # Try in-cluster config first
    config.load_incluster_config()
except:
    # Fallback to kubeconfig file
    kubeconfig_path = os.environ.get("KUBECONFIG", "~/.kube/config")
    config.load_kube_config(kubeconfig_path)

# Initialize Kubernetes API clients
v1 = client.CoreV1Api()
apps_v1 = client.AppsV1Api()

@mcp.tool
def list_pods(namespace: str = "default") -> Dict[str, Any]:
    """List all pods in the specified namespace."""
    try:
        pods = v1.list_namespaced_pod(namespace=namespace)
        pod_list = [
            {
                "name": pod.metadata.name,
                "namespace": pod.metadata.namespace,
                "status": pod.status.phase,
                "ip": pod.status.pod_ip,
            }
            for pod in pods.items
        ]
        return {"success": True, "pods": pod_list}
    except Exception as e:
        return {"success": False, "error": str(e)}

@mcp.tool
def create_nginx_pod(pod_name: str, namespace: str = "default") -> Dict[str, Any]:
    """Create an nginx pod in the specified namespace."""
    try:
        pod = client.V1Pod(
            metadata=client.V1ObjectMeta(name=pod_name, namespace=namespace),
            spec=client.V1PodSpec(
                containers=[
                    client.V1Container(
                        name="nginx",
                        image="nginx:latest",
                        ports=[client.V1ContainerPort(container_port=80)],
                    )
                ]
            ),
        )
        v1.create_namespaced_pod(namespace=namespace, body=pod)
        return {"success": True, "message": f"Pod {pod_name} created in namespace {namespace}"}
    except Exception as e:
        return {"success": False, "error": str(e)}

@mcp.tool
def get_pod_logs(pod_name: str, namespace: str = "default") -> Dict[str, Any]:
    """Retrieve logs for a specified pod in the given namespace."""
    try:
        logs = v1.read_namespaced_pod_log(name=pod_name, namespace=namespace)
        return {"success": True, "logs": logs}
    except Exception as e:
        return {"success": False, "error": str(e)}

@mcp.tool
def delete_pod(pod_name: str, namespace: str = "default") -> Dict[str, Any]:
    """Delete a specified pod in the given namespace."""
    try:
        v1.delete_namespaced_pod(name=pod_name, namespace=namespace)
        return {"success": True, "message": f"Pod {pod_name} deleted from namespace {namespace}"}
    except Exception as e:
        return {"success": False, "error": str(e)}

if __name__ == "__main__":
    mcp.run()