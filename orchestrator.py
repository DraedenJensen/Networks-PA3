import docker
import argparse
import subprocess

parser = argparse.ArgumentParser(prog = 'OSPF orchestrator', 
                                 description='An application for creating and managing a four-node topology with two hosts featuring traffic control between a north and south route')
g = parser.add_mutually_exclusive_group(required=True)
g.add_argument("-c", "--construct", action="store_true", help="construct or rebuild the four-node network topology")
g.add_argument("-d", "--daemons", action="store_true", help="start up OSPF daemons with appropriate configurations in the routed network topology")
g.add_argument("-r", "--routes", action="store_true", help="install routes connecting the hosts and endpoints in the routed network topology")
g.add_argument("-n", "--north", action="store_true", help="direct network traffic to the north path (via router R2)")
g.add_argument("-s", "--south", action="store_true", help="direct network traffic to the south path (via router R4)")
g.add_argument("-q", "--quit", action="store_true", help="disconnect the network topology")
args = parser.parse_args()

client = docker.from_env()

if args.construct:
    print("Beginning construction of the four-node topology...")
    print("Building networks...")

    def add_network(name, subnet):
        try:
            print(f"Checking for network {name} in existing environment...")
            network = client.networks.get(name)
            print(f"Network {name} already exists, removing...")
            for ctnr in network.containers:
                print(f"Disconnecting {ctnr.name} from {name}...")
                network.disconnect(ctnr)
            network.remove()
            print(f"Finished removing {name}, rebuilding...")
        except docker.errors.NotFound:
            print(f"Building network {name}...")
            
        client.networks.create(name, driver="bridge",
        ipam=docker.types.IPAMConfig(pool_configs=[
            docker.types.IPAMPool(subnet=subnet)
        ]))
        print(f"Network {name} created successfully with subnet {subnet}")

    add_network("net12", "10.0.12.0/24")
    add_network("net14", "10.0.14.0/24")
    add_network("net23", "10.0.23.0/24")
    add_network("net34", "10.0.34.0/24")
    print("All networks created, building containers for routers and hosts...")

    image, _ = client.images.build(path=".", tag="image")
    def add_container(name, subnet_addresses):
        try:
            print(f"Checking for network {name} in existing environment...")
            container = client.containers.get(name)
            print(f"Container {name} already exists, removing...")
            container.stop()
            container.remove()
            print(f"Finished removing {name}, rebuilding...")
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
        print(f"Container {name} created and connected to the network")

    add_container("r1", [("net12", "10.0.12.5"), ("net14", "10.0.14.5")])
    add_container("r2", [("net12", "10.0.12.2"), ("net23", "10.0.23.2")])
    add_container("r3", [("net23", "10.0.23.3"), ("net34", "10.0.34.3")])
    add_container("r4", [("net14", "10.0.14.4"), ("net34", "10.0.34.4")])
    add_container("ha", [("net12", "10.0.12.9")])
    add_container("hb", [("net34", "10.0.34.9")])

    print("All networks and nodes created, exiting")
if args.daemons:
    print("Beginning OSPF daemon setup...")
    if len(client.containers.list()) == 0:
        print("Error: no containers connected, exiting")
    else:
        for container in client.containers.list():
            if (container.name == "ha" or container.name == "hb"):
                continue
            print(f"Beginning setup for {container.name}...")
            print("...")
            print("...")
            subprocess.run(f"docker exec -it {container.name} apt -y install curl", shell=True)
            subprocess.run(f"docker exec -it {container.name} apt -y install gnupg", shell=True)
            subprocess.run(f"docker exec -it {container.name} sh -c \"curl -s https://deb.frrouting.org/frr/keys.gpg | tee /usr/share/keyrings/frrouting.gpg > /dev/null\"", shell=True)
            subprocess.run(f"docker exec -it {container.name} apt -y install lsb-release", shell=True)            subprocess.run(f"docker exec -it {container.name} sh -c \"echo deb '[signed-by=/usr/share/keyrings/frrouting.gpg]' https://deb.frrouting.org/frr $(lsb_release -s -c) frr-stable | tee -a /etc/apt/sources.list.d/frr.list\"", shell=True)
            subprocess.run(f"docker exec -it {container.name} sh -c \"apt update && apt -y install frr frr-pythontools\"", shell=True)
            subprocess.run(f"docker exec -it {container.name} sed -i 's/ospfd=no/ospfd=yes/' /etc/frr/daemons", shell=True)
            subprocess.run(f"docker exec -it {container.name} service frr restart", shell=True)
            print("...")
            print("...")
            print(f"OSPF daemon setup complete for {container.name}")
            print("...")
        print("Finished OSPF daemon setup, exit")
if args.routes:
    print("Beginning OSPF route setup...")
    if len(client.containers.list()) == 0:
        print("Error: no containers connected, exiting")
    else:
        for container in client.containers.list():
            print(f"Beginning setup for {container.name}...")
            router = True
            match container.name:
                case "ha":
                    net = "10.0.34.0/24 gw 10.0.12.5"
                    router = False
                case "hb":
                    net = "10.0.12.0/24 gw 10.0.34.3"
                    router = False
                case "r1":
                    net1 = "10.0.12.0/24"
                    net2 = "10.0.14.0/24"
                case "r2":
                    net1 = "10.0.12.0/24"
                    net2 = "10.0.23.0/24"
                case "r3":
                    net1 = "10.0.23.0/24"
                    net2 = "10.0.34.0/24"
                case "r4":
                    net1 = "10.0.14.0/24"
                    net2 = "10.0.34.0/24"

            if router:
                subprocess.run(f"docker exec -it {container.name} service frr restart", shell=True)
                subprocess.run((f"docker exec -it {container.name} "
                                "vtysh " 
                                "-c 'configure terminal' " 
                                "-c 'router ospf' "
                                f"-c 'network {net1} area 0.0.0.0' " 
                                f"-c 'network {net2} area 0.0.0.0'"), shell=True)
                print(f"Router {container.name} now advertising subnets {net1} and {net2}")
            else:
                subprocess.run(f"docker exec -it {container.name} route add -net {net}", shell=True)
                print(f"Subnet {net[:11]} now visible to host {container.name}")
        print("Finished initial route setup, adding OSPF weights...")
        for container in client.containers.list():
            if container.name == "ha" or container.name == "hb":
                continue
            print(f"Adding weights for {container.name}...")
            subprocess.run((f"docker exec -it {container.name} "
                            "vtysh " 
                            "-c 'configure terminal' " 
                            "-c 'interface eth0' "
                            "-c 'ip ospf cost 10' " 
                            "-c 'end' "
                            "-c 'interface eth1' "
                            "-c 'ip ospf cost 10'"), shell=True)
            print(f"Finished adding weights for {container.name}")
        print("Finished OSPF route setup, exiting")
if args.north:
    pass
if args.south:
    pass
if args.quit:
    print("Beginning destruction of the topology...")
    removed = False
    for container in client.containers.list():
        removed = True
        name = container.name
        print(f"Removing container {name}...")
        container.stop()
        container.remove()
        print(f"Container {name} removed")
    for network in client.networks.list():
        removed = True
        name = network.name
        if name in ["net12", "net23", "net34", "net14"]:
            print(f"Removing network {name}...")
            network.remove()
            print(f"Network {name} removed")
    
    if not removed:
        print("Nothing to remove, exiting")
    else:
        print("Topology disconnected, exiting")