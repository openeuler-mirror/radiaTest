# radiaTest

#### introduce

Test Management Platform

- Version-level quality dashboards enable community version testing to be traceable and traceable
- Diversified resource pools, barrier-free docking of various resource management systems and networks
- Unified management of text use cases provides a foundation for the development and review of community text use cases
- Diversified test engines to meet the needs of differentiated testing capabilities in the community and can be flexibly selected
- Task management and management capabilities to realize the whole process of testing activities

#### Introduction to the Architecture

radiaTest-web & radiaTest-server: Frontend and backend of the web service
- If you need to deploy the test management platform web service locally, you need to deploy it (it is recommended to use the public service provided by the radiatest.openeuler.org)

radiaTest-messenger: Request forwarding and processing service for connecting with the machine group
- A bastion/springboard node for a machine group that communicates with radiaTest-server as a single point
- Deployed on intranet/extranet jump servers, or deployed on intranet machines after NAT mapping
- After registering the corresponding machine group with the web service, the individual/team/organization manager can deploy the corresponding machine as needed

radiaTest-worker: dynamic resource (VM resource) management service
- It is deployed on a physical host to accept requests related to dynamic resources and complete the management of actual VM resources 
- Can be deployed on the intranet of the machine group and only communicates with messenger nodes (recommended)
- If it is deployed on a public network machine, you must ensure that it belongs to a public network machine group and can communicate with the messenger node of the corresponding machine group

#### Installation tutorial

radiaTest-worker must be deployed in the server physical environment (only the host physical machine needs to be deployed)

一、Containerized deployment based on bare metal/virtual machine nodes
1. Installing web service front-end and back-end (radiaTest-web & radiaTest-server)
   1. Install docker and the docker-compose package on the host to be deployed
   2. Execute build/docker -compose/radiatestctl -u web to start the service
   3. Deploy the service according to the interactive guidance, and fill in the certificate inform      ation in the process (the NSL certificate is required for the NGINX service on the web serve      r and messenger side) 4) Modify the /etc/radiaTest/server .ini configuration file
   4. Execute build/docker-compose/radiatestctl -d web to shut down the service
 
2. Installing messenger server (radiatest messenger)
   1. Install docker and the docker-compose package on the host to be deployed
   2. Execute build/docker-compose/radiatestctl -u messenger to start the service
   3. Deploy the service according to the interactive instructions, generate a CSR file and reques      t a signing certificate from the server
   4. Modify the/etc/radiatest/messenger. ini configuration file
   5. Execute build/docker-compose/radiatest -d messenger to shut down the service

3. Installing worker server (radiaTest-worker)
   1. Run the build/docker-compose/radiatest -u worker command to start the service (the worker's       flask application will directly occupy the host port)
   2. Modify the /etc/radiaTest/worker.ini configuration file
   3. Execute build/docker-compose/radiatest -d worker to shut down the service

二、Based on k8s, the deployment node is k8s pod (Currently only covering radiaTest-web & radiaTest-server)
1. Build docker images through the Dockerfiles of build/k8s-pod/web/nginx & build/k8s-pod/web/gunicorn and other celery-workers
2. Prepare Redis, RabbitMQ, and databases, which require manual preparation of middleware and database services
3. Apply the required complete configuration files to the corresponding containers by mounting the directory volume, such as nginx, flask-app, gunicorn, etc
4. Run the container and check the logs and running status

   P.S.
   - Because the flask application is initialized with a configuration file, ambiguous characters such as # % are not allowed to appear directly in the middleware and database passwords, and escaping must be used if needed
   - In the configuration file, it is not recommended to use the domain hostname of the cluster in the IP field, and it is recommended to use 0.0.0.0 directly to ensure access security from the outside
   - Logs are stored in the logs of the working directory of the container and can be managed in the form of attaching a directory volume or storing them in an OBS bucket

#### Operation and maintenance instructions based on containerized deployment of bare metal/virtual machine nodes

If you need to change the service port or the port mapping of docker, please modify the dockerfile or docker-compose.yml ./gunicorn/gunicorn.conf.py to determine the port that flask actually listens on in docker The process logs controlled by the supervisor are in ./log

1. Using web services front-end and back-end (radiaTest-web & radiaTest-server)
   1. docker exec -ti web_supervisor_1 bash
   2. Modify the /etc/radiaTest/server.ini configuration file
   3. Execute the supervisorCTL interactive management service
   4. The nginx configuration file is located in the host /etc/nginx/nginx.conf, and the default H      TTP listener is 8080 and https listener 443

2. Using messenger services (radiaTest-messenger)
   1. docker exec -ti messenger_supervisor_1 bash    
   2. Modify the /etc/radiaTest/messenger.ini configuration file
   3. Execute the supervisorCTL interactive management service 

3. Using worker services (radiaTest-worker)

#### Get involved

1. Fork this repository
2. Create a new Feat_xxx branch (optional)
3. Submit the code
4. Create a new pull request

#### Commit Specifications > Quality Requirements

1. commit format 
   1. The commit name must be in the format type(scope): subject 
   2. Type only allows the use of the following identifiers:
      - FEAT: New Feature
      - fix/to: fixes bugs, which can be bugs discovered by QA or discovered by R&D
      - fix: Generates a diff and fixes this issue automatically. Ideal for fixing issues directly             with a single commit
      - to: Generating only diff does not automatically fix this issue. Suitable for multiple subm            issions. The final fix is fixed when submitted
      - docs: documentation
      - style: format (changes that do not affect the operation of the code)
      - refactor: Refactoring (i.e., not a new feature, nor a code change to fix a bug)
      - perf: optimization-related, such as improving performance and experience
      - test: adds a test. chore: Changes to the build process or auxiliary tools
      - revert: rolls back to the previous version. merge: code merge
      - sync: Synchronization bug of the main line or branch
    3. Scope is an optional option that describes the scope (interface, class, method) of the commit.

    4. The subject must be a commit description and must be less than 50 characters

2. Access control requirements 
   1. PRs that pass all access control tests will be merged if and only if they are passed
   2. If there are problems such as misjudgment or unnecessary checks, the commit submitter must log in to the MaJun platform to submit a blocking application for the corresponding check items anddesignate Ethan-Zhang for review 
   3. If the block request is approved, the PR will be merged after the rerun result is passed 
   4. If the blocking request is rejected, the PR will remain in the original state, and the developer needs to complete the corresponding modifications, manually /retest to complete the re-check, and @Ethan-Zhang to notify the merge after the gate control is passed

3. Test coverage
   1. For each PR, the test coverage must meet the standard of 80% test coverage
   2. For commits that do not involve new features, interfaces, classes, or methods, you need to attach screenshots of the existing test results/reports involved in the PR comments
   3. For commits involving new features, interfaces, classes, and methods, the corresponding developer self-test cases need to be attached to the PR, and screenshots of the test results/reports involving the interface need to be attached to the PR

4. issue 
   1. If there is no issue in the repository that describes the problem to be fixed, you need to create an issue and then submit a PR associated with the issue, otherwise it will not be merged

#### Contact

Ethan-Zhang: 
     - EMAIL ethanzhang55@outlook.com

#### stunt

1. Use Readme_XXX.md to support different languages, such as Readme_en.md, Readme_zh.md
2. Gitee Official Blog blog.gitee.com
3. You can https://gitee.com/explore this address to learn about the best open source projects on Gitee
4. GVP stands for Gitee's Most Valuable Open Source Project, and it is an excellent open source project that has been comprehensively evaluated
5. The official Gitee user manual https://gitee.com/help
6. The Gitee Cover Character is a section that showcases Gitee members https://gitee.com/gitee-stars/
