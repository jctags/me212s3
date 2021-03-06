#!/usr/bin/python

# 2.12 Lab 3 AprilTag Navigation: use AprilTag for current global robot (X,Y,Theta), and to navigate to target (X,Y,Theta)
# Peter Yu Sept 2016

import rospy
import tf
import numpy as np
import threading
import serial
import pdb
import traceback
import sys
import tf.transformations as tfm

from apriltags.msg import AprilTagDetections
from me212pillbed.msg import WheelVelCmd
import helper

class ApriltagNavigator():
    def __init__(self):
        self.listener = tf.TransformListener()
        self.br = tf.TransformBroadcaster()
        self.apriltag_sub = rospy.Subscriber("/apriltags/detections", AprilTagDetections, self.apriltag_callback, queue_size = 1)
        
        self.velcmd_pub = rospy.Publisher("/cmdvel", WheelVelCmd, queue_size = 1)   ##

        #rospy.init_node('apriltag_navi', anonymous=True)

        rospy.sleep(1)
        
    def apriltag_callback(self, data):
        # use apriltag pose detection to find where is the robot
        ##
        for detection in data.detections:
            tagframename = '/apriltag' + str(detection.id)
            pose_tag_base = helper.poseTransform(helper.pose2list(detection.pose),  homeFrame = '/camera', targetFrame = '/base_link', listener = self.listener)
            pose_base_map = helper.poseTransform(helper.invPoseList(pose_tag_base), homeFrame = tagframename, targetFrame = '/map', listener = self.listener)
            helper.pubFrame(self.br, pose = pose_base_map, frame_id = '/base_link', parent_frame_id = '/map', npub = 1)
        
    def navigate(self, target_pose2d= [0.25, 0, np.pi]):
        
        ##
        wv = WheelVelCmd()
        target_position2d = target_pose2d[0:2]

        ## 
        arrived = False
        arrived_position = False

        print target_pose2d
        
        while not rospy.is_shutdown() :
            
            ## 
            # 1. get robot pose
            robot_pose3d = helper.lookupTransformList('/map', '/base_link', self.listener)
            
            if robot_pose3d is None:
                try:
                    velocity = (wv.desiredWV_R +wv.desiredWV_L)
                    yaw = robot_pose2d[2]

                    dx = velocity*math.cos(yaw)*0.01
                    dy = velocity*math.sin(yaw)*0.01
                    dyaw = ((wv.desiredWV_R-wv.desiredWV_L)/2)/0.225*0.01
                    newyaw = yaw + dyaw
                    if newyaw > 2*np.pi:
                        newyaw = newyaw - 2*np.pi
                    robot_pose2d=[robot_pose2d[0]+dx,robot_pose2d[1]+dy,newyaw]
                except:
                    robot_pose2d = [0.2,0.2,np.pi/2]
                robot_position2d = robot_pose2d[0:2]
                robot_yaw = robot_pose2d[2]


            else:
            
                robot_position2d = robot_pose3d[0:2]
                
                robot_yaw = tfm.euler_from_quaternion(robot_pose3d[3:7]) [2]
                robot_pose2d = robot_position2d + [robot_yaw]
            
            # 2. navigation policy
            # 2.1 if       in the target, 
            # 2.2 else if  close to target position, turn to the target orientation
            # 2.3 else if  in the correct heading, go straight to the target position,
            # 2.4 else     turn in the direction of the target position
            
            pos_delta = np.array(target_position2d) - np.array(robot_position2d)
            robot_heading_vec = np.array([np.cos(robot_yaw), np.sin(robot_yaw)])
            heading_err_cross = helper.cross2d( robot_heading_vec, pos_delta / np.linalg.norm(pos_delta) )
            
            print 'robot_position2d', robot_position2d, 'target_position2d', target_position2d
            print 'pos_delta', pos_delta
            print 'robot_yaw', robot_yaw
            # print 'norm delta', np.linalg.norm( pos_delta ), 'diffrad', diffrad(robot_yaw, target_pose2d[2])
            # print 'heading_err_cross', heading_err_cross
            
            if (np.linalg.norm( pos_delta ) < 0.08 and np.fabs(helper.diffrad(robot_yaw, target_pose2d[2]))<0.6) :
                print "done!"
                wv.desiredWV_R = 0  
                wv.desiredWV_L = 0
                arrived = True
            elif np.linalg.norm( pos_delta ) < 0.08:
                print "at the desired position"
                print "angle difference", robot_yaw-target_pose2d[2]
                if helper.diffrad(robot_yaw, target_pose2d[2]) > 0:
                    #print 'Case 2.2.1  Turn right slowly'      
                    wv.desiredWV_R = -0.05 
                    wv.desiredWV_L = 0.05
                else:
                    #print 'Case 2.2.2  Turn left slowly'
                    wv.desiredWV_R = 0.05  
                    wv.desiredWV_L = -0.05
                    
            elif np.fabs( heading_err_cross ) < 0.2:
                #print 'Case 2.3  Straight forward'  
                wv.desiredWV_R = 0.1
                wv.desiredWV_L = 0.1
            else:
                if heading_err_cross < 0:
                    #print 'Case 2.4.1  Turn right'
                    wv.desiredWV_R = -0.1
                    wv.desiredWV_L = 0.1
                else:
                    #print 'Case 2.4.2  Turn left'
                    wv.desiredWV_R = 0.1
                    wv.desiredWV_L = -0.1
                    
            #print(wv)
            self.velcmd_pub.publish(wv)  

            if arrived:
                print "moving on"
                return
            
            rospy.sleep(0.01)
   
'''

def main():
    rospy.init_node('me212_robot', anonymous=True)
    april_navi = ApriltagNavigator()
    rospy.spin()

if __name__=='__main__':
    main()

'''
    
