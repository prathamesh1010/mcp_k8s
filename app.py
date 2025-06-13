import mcpi.minecraft as minecraft
import mcpi.block as block
from kubernetes import client, config
import spacy
import time
import asyncio
import re
from threading import Thread

# Initialize Minecraft server connection
mc = minecraft.Minecraft.create()

# Load Kubernetes configuration
try:
    config.load_kube_config()  # Assumes kubeconfig is in default location (~/.kube/config)
except Exception as e:
    print(f"Failed to load Kubernetes config: {e}")
    exit(1)

# Initialize Kubernetes API clients
v1 = client.AppsV1Api()
core_v1 = client.CoreV1Api()

# Load spaCy model for natural language processing
nlp = spacy.load("en_core_web_sm")

# Dictionary to store deployment templates (simplified)
deployment_templates = {
    "myapp": {
        "image": "nginx:latest",
        "port": 80
    }
}

def create_deployment(name, image, port, replicas=1):
    """Create a Kubernetes deployment."""
    deployment = client.V1Deployment(
        metadata=client.V1ObjectMeta(name=name),
        spec=client.V1DeploymentSpec(
            replicas=replicas,
            selector=client.V1LabelSelector(match_labels={"app": name}),
            template=client.V1PodTemplateSpec(
                metadata=client.V1ObjectMeta(labels={"app": name}),
                spec=client.V1PodSpec(
                    containers=[
                        client.V1Container(
                            name=name,
                            image=image,
                            ports=[client.V1ContainerPort(container_port=port)]
                        )
                    ]
                )
            )
        )
    )
    try:
        v1.create_namespaced_deployment(namespace="default", body=deployment)
        return f"Deployed {name} successfully."
    except Exception as e:
        return f"Error deploying {name}: {str(e)}"

def scale_deployment(name, replicas):
    """Scale a Kubernetes deployment."""
    try:
        v1.patch_namespaced_deployment_scale(
            name=name,
            namespace="default",
            body={"spec": {"replicas": replicas}}
        )
        return f"Scaled {name} to {replicas} replicas."
    except Exception as e:
        return f"Error scaling {name}: {str(e)}"

def delete_deployment(name):
    """Delete a Kubernetes deployment."""
    try:
        v1.delete_namespaced_deployment(name=name, namespace="default")
        return f"Deleted {name} successfully."
    except Exception as e:
        return f"Error deleting {name}: {str(e)}"

def list_pods():
    """List all pods in the default namespace."""
    try:
        pods = core_v1.list_namespaced_pod(namespace="default")
        pod_names = [pod.metadata.name for pod in pods.items]
        return f"Pods: {', '.join(pod_names)}"
    except Exception as e:
        return f"Error listing pods: {str(e)}"

def parse_command(text):
    """Parse natural language command using spaCy."""
    doc = nlp(text.lower())
    action = None
    target = None
    value = None

    # Simple keyword-based parsing
    if any(token.text in ["deploy", "create"] for token in doc):
        action = "deploy"
        for token in doc:
            if token.text in deployment_templates:
                target = token.text
    elif any(token.text in ["scale", "resize"] for token in doc):
        action = "scale"
        for token in doc:
            if token.text in deployment_templates:
                target = token.text
        # Extract number for replicas
        numbers = re.findall(r'\d+', text)
        if numbers:
            value = int(numbers[0])
    elif any(token.text in ["delete", "remove"] for token in doc):
        action = "delete"
        for token in doc:
            if token.text in deployment_templates:
                target = token.text
    elif any(token.text in ["list", "show"] for token in doc):
        action = "list"

    return action, target, value

async def handle_minecraft_commands():
    """Handle Minecraft chat commands."""
    while True:
        try:
            for chat in mc.events.pollChatPosts():
                command = chat.message
                mc.postToChat(f"Received command: {command}")
                action, target, value = parse_command(command)

                if action == "deploy" and target:
                    template = deployment_templates.get(target, {})
                    response = create_deployment(
                        target,
                        template.get("image", "nginx:latest"),
                        template.get("port", 80)
                    )
                    mc.postToChat(response)
                elif action == "scale" and target and value:
                    response = scale_deployment(target, value)
                    mc.postToChat(response)
                elif action == "delete" and target:
                    response = delete_deployment(target)
                    mc.postToChat(response)
                elif action == "list":
                    response = list_pods()
                    mc.postToChat(response)
                else:
                    mc.postToChat("Invalid command or target not found.")
        except Exception as e:
            mc.postToChat(f"Error processing command: {str(e)}")
        await asyncio.sleep(0.1)

def run_async_loop():
    """Run the async command handler in a separate thread."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(handle_minecraft_commands())

if __name__ == "__main__":
    print("Starting MCP Kubernetes control server...")
    # Start the async command handler in a separate thread
    thread = Thread(target=run_async_loop)
    thread.daemon = True
    thread.start()

    # Keep the main thread running
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Shutting down server...")