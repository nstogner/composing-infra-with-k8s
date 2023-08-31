# Composing Infrastructure with Kubernetes

This repo explores how to compose together low-level Crossplane APIs (Managed Resources) using higher level APIs (Claims) using alternatives to the Crossplane Composition construct. Crossplane Compositions are expressed as YAML and currently lack the following functionality which quickly becomes necessary when creating platform APIs:

* Conditionals (ex: `if` field X is set, conditionally create resource Y)
* Loops (ex: `for` each field X, create a matching resource Y)

A note about Crossplane Providers: Compared to alternatives ([AWS ACK](https://aws-controllers-k8s.github.io/community/), [GCP Config Connector](https://github.com/GoogleCloudPlatform/k8s-config-connector)), Crossplane Provider resources (MRs) are unique in that they are [Cluster-scoped](https://kubernetes.io/docs/reference/using-api/api-concepts/#resource-uris). This repo currently explores the implications of working with cluster-scoped Crossplane MRs resources and will leave the comparison of the alternative solutions to Crossplane Providers to a later date.

## Alternative 1: Crossplane Composition Functions

Crossplane functions (XFNs) were created to address the shortcomings of Compositions. Functions provides the ability to execute arbitrary containers as a part of the process of composing resources. XFNs will not be considered as an alternative to Compositions here due to their complexity.

## Alternative 2: Helm Charts via FluxCD

Example: `./helmplane/`

Helm is commonly used for translating a set of parameters (`values.yaml` file) into a set of Kubernetes resources. Helm charts (Go templates) can be used to express conditional logic along with loops. The `helm` CLI command is typically run outside of the cluster and applies resources against the Kubernetes API at a point in time. The FluxCD Helm controller extends this functionality and creates an API for applying charts.

In this design, the FluxCD HelmRelease resource takes the place of the Crossplane Claim.

*Pros*

* HelmRelease is Namespaced - but it can manage Cluster-scoped resources (HelmRelease parent-child relationships are tracked outside of Kubernetes `ownerReferences`).
* Helm charts are commonplace in Kubernetes and easy for administrators to author.

*Cons*

* There is no mechanism to map output values from one MR into the input values of another.
* Helm charts are foreign to non-Kubernetes practitioners.

## Alternative 3: Metacontroller

Example: `./metaplane/crd/`

Metacontroller extends Kubernetes with the ability to author watch-based controllers as webhooks. Metacontroller is written in Go and takes care of most of the complicated parts of authoring controllers: wiring up watches, caches, etc. The user can author a controller using any programming language.

*Pros*

* Teams are free to choose the language they prefer when writing controllers.
* Metacontroller can operate against any Kubernetes resource type (your own CRD, or even Crossplane XRDs).
* Metacontroller reacts to changes to children.
* It is possible to map values from child resources to other child resources.

*Cons*

* Slightly more complex than Helm chart.
* Metacontroller uses built-in Kubernetes `ownerReferences` to track parent-child relationships. To play nicely with Crossplane MRs, Metacontroller parents must also be Cluster-scoped.

### Variation: Metacontroller with XRD

To allow for Namespaced resources to be created, Metacontroller can be configured to act upon Crossplane Composite resources (defined by XRDs). Crossplane's XRD controller will create a Namespaced and a Cluster-scoped CRD and handle the replication of the Namespaced Claim to the Cluster-scoped Composite.

Example: `./metaplane/xrd/`

*Pros*

* Namespaced parent resources (Claims).

*Cons*

* Without a Composition the Claim reports a Synced status but never reports a Ready status:

```bash
kubectl get multibuckets.example.org
NAME       SYNCED   READY   CONNECTION-SECRET   AGE
heythere   True     False                       138m
```

## Quickstart

```sh
# Re-run if this fails.
make up

# Apply parent resources.
kubectl apply -f ./helmplane/examples
kubectl apply -f ./metaplane/crd/examples
kubectl apply -f ./metaplane/xrd/examples

# Check that the child resources were created.
# The ".s3" part is needed because FluxCD also installed a "kind: Bucket" CRD.
kubectl get buckets.s3

# Check the parent resources that were created.
kubectl get -f ./helmplane/examples
kubectl get -f ./metaplane/crd/examples
kubectl get -f ./metaplane/xrd/examples

# Delete the parent resources.
kubectl delete -f ./helmplane/examples
kubectl delete -f ./metaplane/crd/examples
kubectl delete -f ./metaplane/xrd/examples

# Check that the child resources were deleted.
kubectl get buckets.s3
```
