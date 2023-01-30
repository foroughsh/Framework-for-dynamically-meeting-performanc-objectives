<h1>Overview</h1>

The structure of this framework is shown in the Figure below.

<p align="center">
<img src="https://github.com/foroughsh/dynamically_meeting_performace_objectives_framework/blob/9eb9dc8e04de3e4e9bbeb1c1f3fca135abab6149/framework_small.png" width="500"/>
</p>

As is shown in this figure, to learn the effective policy on this framework efficiently, we take the following 6 steps:

(1) First we define the RL scenario based on the management objectives, available controls in the system, and state of the system.

(2) We run this scenario on the testbed and monitor the system and collect the monitoring data. 

(3) We use this monitoring data and learn the system model.

(4) We use this system model and set up the simulation. We use this simulation to learn the control policy using an RL agent.

(5) We evaluate the learned policy on the simulator for the seen and unseen load patterns.

(6) We evaluate the learned policy on the testbed for the seen and unseen load pattern.

<h1>Set up the testbed</h1>

To set up the testbed, we need to take the following steps:

(1) Install Kubernetes cluster and Istio as our orchestration tool and the service mesh framework. 

(2) Deploy the application microservices by running the ymal files on the master node of our K8 cluster. We need to also configure the virtual services for Istio. 

(3) Test the deployed application by running one of the clients or by sending a request in the web browser. 

(4) Now the testbed is ready!


The files for testbed set up are under the folders
 
+ K8_and_Istio_installation
 
+ Services_on_testbed: This folder includes the source code of the microservices deployed on testbed for later changes. Moreover, the ymal files to deploy the services are in this folder. 
 
+ Load_generator
 

<h1>Data collection</h1>

In this step, we need to run the RL scenario on the testbed and monitor the testbed and collect the samples. We prepare the script that runs the load generators with the specified load pattern and saves the collected samples.  


This part runs only on the testbed. 

The files for this section can be found in data_collection. This folder includes the scripts to run the load generators and save the observations.   

<h1>Learnign system model</h1>

After we collect the data from the testbed, we can apply any supervised learning, such as random forest, and save the learned model.

This part runs on the local system. 

The files for this section can be found in system_model. The file generates the system model, cleans the collected observations and removes the outliers and trains the random forest model.   


<h1>Learnign and evaluation of the control policy on the simulator</h1>

We use the learned control policy from the previous step and learn the control policy by using the RL model. We check the learning curve every 4000 steps and then if the learned control policy is converged to the optimal policy, we save the RL model for later evaluation. 


This part runs on the local system. 

The files for this section can be found in training.    


<h1>Evalutation of the control policy on the testbed</h1>

In this part, run the load generators on the testbed and evaluate the saved model. 


This part runs on the testbed. 

