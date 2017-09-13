# # from flask import url_for
# from flask_sqlalchemy import SQLAlchemy
# import os
#
# db = SQLAlchemy()
#
#
# class CodeUpgradeJob(db.Model):
#     __tablename__ = 'CodeUpgrades'
#     id = db.Column(db.Integer, primary_key=True)
#     device = db.Column(db.String(64))
#     username = db.Column(db.String(32))
#     mop = db.Column(db.String(64),
#                     default="unknown")
#
#     images_url = db.Column(db.String(128))
#     regions_url = db.Column(db.String(128))
#     logbin_url = db.Column(db.String(128))
#
#     target_image = db.Column(db.String(128))
#
#     status = db.Column(db.String(128),
#                        default="SUBMITTED")
#     status_log_url = db.Column(db.String(128),
#                                default=None)
#     code_upload_status = db.Column(db.String(128),
#                                    default="default")
#     code_upload_log_url = db.Column(db.String(128),
#                                     default=None)
#     sup_redundancy_status = db.Column(db.String(128),
#                                       default="default")
#     sup_redundancy_log_url = db.Column(db.String(128),
#                                        default=None)
#     copy_code_to_slave_status = db.Column(db.String(128),
#                                           default="default")
#     copy_code_to_slave_log_url = db.Column(db.String(128),
#                                            default=None)
#     backup_running_config_status = db.Column(db.String(128),
#                                              default="default")
#     backup_running_config_log_url = db.Column(db.String(128),
#                                               default=None)
#     set_bootvar_status = db.Column(db.String(128),
#                                    default="default")
#     set_bootvar_status_log_url = db.Column(db.String(128),
#                                            default=None)
#     verify_bootvar_status = db.Column(db.String(128),
#                                       default="default")
#     verify_bootvar_status_log_url = db.Column(db.String(128),
#                                               default=None)
#     reload_status = db.Column(db.String(128),
#                               default="default")
#     reload_status_log_url = db.Column(db.String(128),
#                                       default=None)
#     verify_upgrade = db.Column(db.String(128),
#                                default="default")
#     verify_upgrade_log_url = db.Column(db.String(128),
#                                        default=None)
#     custom_verification_1_name = db.Column(db.String(128),
#                                            default="Custom Verification 1")
#     custom_verification_1_status = db.Column(db.String(128),
#                                              default="default")
#
#     custom_verification_1_status_log_url = db.Column(db.String(128),
#                                                      default=None)
#
#     custom_verification_2_name = db.Column(db.String(128),
#                                            default="Custom Verification 2")
#
#     custom_verification_2_status = db.Column(db.String(128),
#                                              default="default")
#
#     custom_verification_2_status_log_url = db.Column(db.String(128),
#                                                      default=None)
#
#     def __init__(self, device, username, password, mop_name):
#
#         self.device = device
#         self.username = username
#         self.password = password
#         self.mop = mop_name
#         self.regions_url = os.getenv('REGIONS_API')
#         self.images_url = os.getenv('IMAGES_API')
#         self.logbin_url = os.getenv('LOGBIN_API')
#
#     @property
#     def steps(self):
#         """
#         this code is used to render steps in the template
#         :return:
#         """
#         steps = [('Code Transfer', self.code_upload_status, self.code_upload_log_url),
#                 ('Verify Supervisor Redundancy', self.sup_redundancy_status, self.sup_redundancy_log_url),
#                 ('Synchronize Code to Standby Supervisor', self.copy_code_to_slave_status, self.copy_code_to_slave_log_url),
#                 ('Backup Running Config', self.backup_running_config_status, self.backup_running_config_log_url),
#                 ('Set Boot Variable', self.set_bootvar_status, self.set_bootvar_status_log_url),
#                 ('Verify Boot Variable', self.verify_bootvar_status, self.verify_bootvar_status_log_url),
#                 ('Reload Device', self.reload_status, self.reload_status_log_url),
#                 ('Verify Upgrade', self.verify_upgrade, self.verify_upgrade_log_url, self.verify_upgrade_log_url),
#                 (self.custom_verification_1_name, self.custom_verification_1_status, self.custom_verification_1_status_log_url),
#                 (self.custom_verification_2_name, self.custom_verification_2_status, self.custom_verification_2_status_log_url)
#               ]
#         return steps
#
#     def as_dict(self):
#         return {"id": self.id,
#                 "device":
#                     self.device,
#                 "username":
#                     self.username,
#                 "mop":
#                     self.mop,
#                 "status":
#                     self.status,
#                 "target_image":
#                     self.target_image,
#                 "status_log_url":
#                     self.status_log_url,
#                 "code_upload_status":
#                     self.code_upload_status,
#                 "code_upload_log_url":
#                     self.code_upload_log_url,
#                 "sup_redundancy_status":
#                     self.sup_redundancy_status,
#                 "sup_redundancy_log_url":
#                     self.sup_redundancy_log_url,
#                 "copy_code_to_slave_status":
#                     self.copy_code_to_slave_status,
#                 "copy_code_to_slave_log_url":
#                     self.copy_code_to_slave_log_url,
#                 "set_bootvar_status":
#                     self.set_bootvar_status,
#                 "set_bootvar_status_log_url":
#                     self.set_bootvar_status_log_url,
#                 "backup_running_config_status":
#                     self.backup_running_config_status,
#                 "backup_running_config_log_url":
#                     self.backup_running_config_log_url,
#                 "verify_bootvar_status":
#                     self.verify_bootvar_status,
#                 "verify_bootvar_status_log_url":
#                     self.verify_bootvar_status_log_url,
#                 "reload_status":
#                     self.reload_status,
#                 "reload_status_log_url":
#                     self.reload_status_log_url,
#                 "verify_upgrade":
#                     self.verify_upgrade,
#                 "verify_upgrade_log_url":
#                     self.verify_upgrade_log_url,
#                 "custom_verification_1_name":
#                     self.custom_verification_1_name,
#                 "custom_verification_1_status":
#                     self.custom_verification_1_status,
#                 "custom_verification_1_status_log_url":
#                     self.custom_verification_1_status_log_url,
#                 "custom_verification_2_name":
#                     self.custom_verification_2_name,
#                 "custom_verification_2_status":
#                     self.custom_verification_2_status,
#                 "custom_verification_2_status_log_url":
#                     self.custom_verification_2_status_log_url,
#                 "regions_url":
#                     self.regions_url,
#                 "images_url":
#                     self.images_url,
#                 "logbin_url":
#                     self.logbin_url
#                 }
#
#     @classmethod
#     def from_dict(cls, job_dict):
#         obj = cls(job_dict['device'],
#                   job_dict['username'],
#                   job_dict['password'],
#                   job_dict['mop'])
#
#         for k, v in job_dict.items():
#             setattr(obj, k, v)
#         return obj
#
#     def save(self):
#         db.session.add(self)
#         db.session.commit()
#
#     def delete(self):
#         db.session.delete(self)
#         db.session.commit()
#
#     def update_status(self, status):
#         self.status = status
#         self.save()
