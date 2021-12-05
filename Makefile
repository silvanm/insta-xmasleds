deploy:
	docker login -u serviceaccount -p (oc whoami -t) registry.appuio.ch
	docker build -t registry.appuio.ch/silvan-privat/xmaslights .
	docker push registry.appuio.ch/silvan-privat/xmaslights:latest
