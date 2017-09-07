from flask import url_for
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class CodeUpgradeJob(db.Model):
    __tablename__ = 'CodeUpgrades'
    id = db.Column(db.Integer, primary_key=True)
    device = db.Column(db.String(64))
    username = db.Column(db.String(32))

    images_url = db.Column(db.String(128))
    regions_url = db.Column(db.String(128))
    logbin_url = db.Column(db.String(128))

    target_image = db.Column(db.String(128))

    status = db.Column(db.String(18),
                       default="SUBMITTED")
    status_log_url = db.Column(db.String(128),
                               default=None)
    code_upload_status = db.Column(db.String(128),
                                   default="default")
    code_upload_log_url = db.Column(db.String(128),
                                    default=None)
    sup_redundancy_status = db.Column(db.String(128),
                                      default="default")
    sup_redundancy_log_url = db.Column(db.String(128),
                                       default=None)
    copy_code_to_slave_status = db.Column(db.String(128),
                                          default="default")
    copy_code_to_slave_log_url = db.Column(db.String(128),
                                           default=None)
    backup_running_config_status = db.Column(db.String(128),
                                             default="default")
    backup_running_config_log_url = db.Column(db.String(128),
                                              default=None)
    set_bootvar_status = db.Column(db.String(128),
                                   default="default")
    set_bootvar_status_log_url = db.Column(db.String(128),
                                           default=None)
    verify_bootvar_status = db.Column(db.String(128),
                                      default="default")
    verify_bootvar_status_log_url = db.Column(db.String(128),
                                              default=None)
    reload_status = db.Column(db.String(128),
                              default="default")
    reload_status_log_url = db.Column(db.String(128),
                                      default=None)
    verify_upgrade = db.Column(db.String(128),
                               default="default")
    verify_upgrade_log_url = db.Column(db.String(128),
                                       default=None)
    verify_fpga_upgrade_status = db.Column(db.String(128),
                                           default="default")
    verify_fpga_upgrade_status_log_url = db.Column(db.String(128),
                                                   default=None)

    def __init__(self, device, username, password):

        self.device = device
        self.username = username
        self.password = password

        self.regions_url = url_for('regions', _external=True)
        self.images_url = url_for('images', _external=True)
        self.logbin_url = url_for('logbin', _external=True)

    def as_dict(self):
        return {"id": self.id,
                "device":
                    self.device,
                "username":
                    self.username,
                "status":
                    self.status,
                "target_image":
                    self.target_image,
                "status_log_url":
                    self.status_log_url,
                "code_upload_status":
                    self.code_upload_status,
                "code_upload_log_url":
                    self.code_upload_log_url,
                "sup_redundancy_status":
                    self.sup_redundancy_status,
                "sup_redundancy_log_url":
                    self.sup_redundancy_log_url,
                "copy_code_to_slave_status":
                    self.copy_code_to_slave_status,
                "copy_code_to_slave_log_url":
                    self.copy_code_to_slave_log_url,
                "set_bootvar_status":
                    self.set_bootvar_status,
                "set_bootvar_status_log_url":
                    self.set_bootvar_status_log_url,
                "backup_running_config_status":
                    self.backup_running_config_status,
                "backup_running_config_log_url":
                    self.backup_running_config_log_url,
                "verify_bootvar_status":
                    self.verify_bootvar_status,
                "verify_bootvar_status_log_url":
                    self.verify_bootvar_status_log_url,
                "reload_status":
                    self.reload_status,
                "reload_status_log_url":
                    self.reload_status_log_url,
                "verify_upgrade":
                    self.verify_upgrade,
                "verify_upgrade_log_url":
                    self.verify_upgrade_log_url,
                "verify_fpga_upgrade_status":
                    self.verify_fpga_upgrade_status,
                "verify_fpga_upgrade_status_log_url":
                    self.verify_fpga_upgrade_status_log_url,
                "regions_url":
                    self.regions_url,
                "images_url":
                    self.images_url,
                "logbin_url":
                    self.logbin_url
                }

    @classmethod
    def from_dict(cls, job_dict):
        obj = cls(job_dict['device'],
                  job_dict['username'],
                  job_dict['password'])

        for k, v in job_dict.items():
            setattr(obj, k, v)
        return obj

    def save(self):
        db.session.add(self)
        db.session.commit()

    def update_status(self, status):
        self.status = status
        self.save()
