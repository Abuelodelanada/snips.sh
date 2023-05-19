# snips.sh Charmed Operator

This repository contains the source code for a Charmed Operator that drives [snips.sh](https://snips.sh/) on Kubernetes.

snips.sh is a passwordless, anonymous SSH-powered pastebin with a human-friendly TUI and web UI.


## Usage

Assuming you have access to a bootstrapped Juju controller on Kubernetes, you can simply:

```shell
juju deploy snips-k8s
```


## OCI Images

This charmed operator uses the [oficial image provided by the upstream](https://ghcr.io/robherley/snips.sh).


## Contributing

Please see the [Juju SDK docs](https://juju.is/docs/sdk) for guidelines on enhancements to this charm following best practice guidelines, and the [contributing](https://github.com/Abuelodelanada/snips-k8s-operator/blob/main/CONTRIBUTING.md) doc for developer guidance.
