.PHONY: kind
kind:
	kind get clusters | grep composing-infra || kind create cluster --name composing-infra

.PHONY: metacontroller
metacontroller:
	kubectl apply -k ./setup/metacontroller
	kubectl wait --for condition=established --timeout=60s crd/compositecontrollers.metacontroller.k8s.io

.PHONY: crossplane
crossplane:
	helm repo add crossplane-stable https://charts.crossplane.io/stable
	helm repo update
	helm upgrade --install crossplane \
	crossplane-stable/crossplane \
	--namespace crossplane-system \
	--create-namespace \
	--wait
	until kubectl get crd/providers.pkg.crossplane.io; do sleep 1; done
	kubectl wait --for condition=established --timeout=120s crd/providers.pkg.crossplane.io

.PHONY: crossplane-aws
crossplane-aws:
	kubectl apply -f ./setup/crossplane/provider-s3.yaml
	kubectl create secret --dry-run=client -oyaml \
	generic aws-secret \
	-n crossplane-system \
	--from-file=creds=${HOME}/.aws/credentials | kubectl apply -f -
	until kubectl get crd/providerconfigs.aws.upbound.io; do sleep 1; done
	kubectl wait --for condition=established --timeout=120s crd/providerconfigs.aws.upbound.io
	kubectl apply -f ./setup/crossplane/provider-s3-config.yaml

.PHONY: metaplane
metaplane:
	kubectl apply -k ./metaplane

.PHONY: fluxcd
fluxcd:
	flux install

.PHONY: fluxcd-config
fluxcd-config:
	kubectl apply -f ./setup/fluxcd/

.PHONY: up
up: kind metacontroller crossplane crossplane-aws metaplane fluxcd

.PHONY: down
down:
	kind delete cluster --name composing-infra

