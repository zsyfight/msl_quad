#!/usr/bin/env python

import rospy
import tf
import std_msgs.msg
from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint
from geometry_msgs.msg import Pose, PoseStamped

#trajectory solve code
from path.objdyn import LoadSim
from path.trajectory import PolynomialTraj, PolynomialTrajOpt
from path.waypoint import Keyframes, KeyframesPool
from path.visual import TrajPlotter

import numpy as np

class Planner:

    def __init__(self):
        rospy.init_node('Planner', anonymous=True)

        self.timeResolution = .2
        self.trajBranchIdx = 3
        self.trans_listener = tf.TransformListener()
        self.speed=1.0 # straight line speed goal, used for calculating time for trajectory
        self.baseHeight=4 #baseheight
        self.pose=None

        #path goal and position goal topics
        self.trajPub = rospy.Publisher('command/trajectory', JointTrajectory, queue_size=10)
        self.poseSub = rospy.Subscriber('mavros/local_position/pose', PoseStamped, self.updatePoseCB)

        rospy.loginfo("Navigation: Planner initalization complete")

    def posePosDist(self, pose):
        #calulates the l2 dist between self.pose and pose
        d = np.array(
            [pose.position.x-self.pose.position.x, 
            pose.position.y-self.pose.position.y,
            pose.position.z-self.pose.position.z])
        return np.linalg.norm(d)


    def updatePoseCB(self, msg):
        #msg is PoseStamped
        self.pose=msg.pose

    def run(self):
        #msg is Pose Stamped
        rospy.loginfo("lucky number 8")
        while self.pose ==None:
            rospy.sleep(.3)
        currentPose=self.pose
        
        #build keyframes

        kf=Keyframes(currentPose.position.x, currentPose.position.y, currentPose.position.z)
        
        #preloaded paths
        # kfpool = KeyframesPool()  
        # kf = kfpool.get_keyframes(name = '003')

        #figure 8, x, y, z, phi
        f8_rel=[(1, 1,  .25, np.pi/2),
                (2, 0,  .5, np.pi),
                (3, -1, .75, np.pi/2.),
                (4, 0,  1, 0),
                (3, 1, .75, -np.pi/2),
                (2, 0, .5, -np.pi),
                (1, -1, .25, -np.pi/2),
                (0, 0, .0, 0)]

        for i,pos_rel in enumerate(f8_rel):
            if i>0 and i<8:
                section_time=4.5
            else:
                section_time=5
            kf.add_waypoint_pos_only(section_time, 
                    currentPose.position.x + pos_rel[0],
                    currentPose.position.y + pos_rel[1],
                    currentPose.position.z+ pos_rel[2],
                    0 + pos_rel[3])
        

        #calculate trajectory
        for wp in kf.wps:
            print wp
        load=LoadSim()

        trajectory = PolynomialTrajOpt(load, kf.wps, kf.ts) 

        #time opt
        # trajectory_time= PolynomialTrajOptTime(load, kf.wps, 
        # tmax=5.3, fz_eq=-19.8, fz_thres=0.5, 
        # taux_thres=0.01, tauy_thres=0.01, tauz_thres=0.01, 
        # n_cycle=5, n_line_search=15)

        # # plot Traj
        # tp = TrajPlotter()
        # tp.plot_traj(trajectory, 'r')
        # tp.show()


        trajMsg=self.buildTrajectoryMsg(trajectory)
        self.trajPub.publish(trajMsg)
        rospy.loginfo("Navigation: Trajectory Sent")



    def buildTrajectoryMsg(self, trajectory):
        #build the trajectory_msgs/JointTrajectory message 
        trajMsg=JointTrajectory()
        print trajectory.ts
        print sum(trajectory.ts)
        for t in np.arange(0.0, sum(trajectory.ts), self.timeResolution):
            #get empty traj pt
            trajPt=JointTrajectoryPoint()
            #get output
            trajPtFlat=trajectory.get_flatout(t)
            print trajPtFlat[:,0]
            #fill point
            trajPt.positions=trajPtFlat[:,0]
            trajPt.velocities=trajPtFlat[:,1]
            trajPt.accelerations=trajPtFlat[:,2]
            trajPt.time_from_start=rospy.Duration.from_sec(t)
            #append to trajectory message
            trajMsg.points.append(trajPt)
        #fill header
        trajMsg.header.stamp = rospy.Time.now()
        trajMsg.header.frame_id = str(1)


        return trajMsg

            


if __name__ == '__main__':
    planner = Planner()
    planner.run()