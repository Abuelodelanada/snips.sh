# snips.sh Charmed Operator

This repository contains the source code for a Charmed Operator that drives [snips.sh](https://snips.sh/) on Kubernetes.

snips.sh is a passwordless, anonymous SSH-powered pastebin with a human-friendly TUI and web UI.


## Deployment

Assuming you have access to a bootstrapped Juju controller on Kubernetes, you can simply:


Create the Juju model where snips.sh will be running.
```shell
juju add-model snips
```

Deploy snips.sh
```shell
juju deploy snips-k8s
```

Deploy traefik`and configure Traefik

```shell
juju deploy traefik-k8s traefik

juju config traefik external_hostname="mysnips.sh"

juju config traefik routing_mode="subdomain"
```

Relate snips.sh to Traefik

```shell
juju relate traefik snips
```

After following these steps, you can check everything is ok:

```shell
$ juju status --color --relations

Model  Controller  Cloud/Region        Version  SLA          Timestamp
snips  microk8s    microk8s/localhost  3.0.3    unsupported  02:27:34-03:00

App      Version  Status  Scale  Charm               Channel  Rev  Address         Exposed  Message
snips             active      1  snips-k8s-operator             8  10.152.183.82   no
traefik  2.9.6    active      1  traefik-k8s         edge     126  192.168.122.10  no

Unit        Workload  Agent  Address     Ports  Message
snips/0*    active    idle   10.1.75.27
traefik/0*  active    idle   10.1.75.61

Relation provider  Requirer       Interface  Type     Message
traefik:ingress    snips:ingress  ingress    regular
```

## Usage

Now you can create your pastebins by simply:

```shell
$ cat src/charm.py | ssh 10.1.75.27 -p 2222
Pseudo-terminal will not be allocated because stdin is not a terminal.
Enter passphrase for key '/home/jose/.ssh/id_rsa':

┃ File Uploaded 📤
┃ id: 1s3bKy2V7q
┃ size: 5.6 kB • type: python • visibility: public

┃ SSH 📠
┃ ssh f:1s3bKy2V7q@localhost -p 2222
┃ URL 🔗
┃ http://snips-snips.mysnips.sh:80/f/1s3bKy2V7q
```


## OCI Images

This charmed operator uses the [official image provided by the upstream](https://ghcr.io/robherley/snips.sh).


## Contributing

Please see the [Juju SDK docs](https://juju.is/docs/sdk) for guidelines on enhancements to this charm following best practice guidelines, and the [contributing](https://github.com/Abuelodelanada/snips-k8s-operator/blob/main/CONTRIBUTING.md) doc for developer guidance.
