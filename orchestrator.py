import docker

client = docker.from_env()

def add_network(name, subnet):
    try:
        client.networks.get(name).remove()
        print(f"Network {name} already exists, removing and rebuilding...")
    except docker.errors.NotFound:
        print(f"Building network {name}...")
        
    client.networks.create(name, driver="bridge",
    ipam=docker.types.IPAMConfig(pool_configs=[
        docker.types.IPAMPool(subnet=subnet)
    ]))
    print(f"Network {name} created with subnet {subnet}")

add_network("net12", "10.0.12.0/24")
add_network("net14", "10.0.14.0/24")
add_network("net23", "10.0.23.0/24")
add_network("net34", "10.0.34.0/24")

image, _ = client.images.build(path=".", tag="image")

def add_container(name, subnet_addresses):
    try:
        client.containers.get(name).remove()
        print(f"Container {name} already exists, removing and rebuilding...")
    except docker.errors.NotFound:
        print(f"Building container {name}...")

    container = client.containers.create(
        image="image",
        name=name,
        stdin_open=True,
        tty=True,
        cap_add=["ALL"],
        privileged=True,
        detach=True
    )

    for tup in subnet_addresses:
        client.networks.get(tup[0]).connect(container, ipv4_address=tup[1])

    container.start()
    print(f"Container {name} created and connected to subnets")

add_container("r1", [("net12", "10.0.12.5"), ("net14", "10.0.14.5")])
add_container("r2", [("net12", "10.0.12.2"), ("net23", "10.0.23.2")])
add_container("r3", [("net23", "10.0.23.3"), ("net34", "10.0.34.3")])
add_container("r4", [("net14", "10.0.14.4"), ("net34", "10.0.34.4")])
add_container("ha", [("net12", "10.0.12.9")])
add_container("hb", [("net34", "10.0.34.9")])

