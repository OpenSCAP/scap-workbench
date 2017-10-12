#ifndef SCAP_WORKBENCH_REMEDIATION_ROLE_SAVER_H_
#define SCAP_WORKBENCH_REMEDIATION_ROLE_SAVER_H_

#include "ForwardDecls.h"
#include "ScanningSession.h"

#include <QString>
#include <QFile>
#include <QFileDialog>

extern "C"
{
#include <xccdf_benchmark.h>
#include <xccdf_policy.h>
#include <xccdf_session.h>
}


class RemediationSaverBase
{
    public:
	RemediationSaverBase(QWidget* parentWindow, ScanningSession* session): mParentWindow(parentWindow), mScanningSession(session) {}
        void SelectFilenameAndSaveRole();

    protected:
        const ScanningSession* mScanningSession;
        QWidget* mParentWindow;

        QString mSaveMessage;
        QString mFiletypeExtension;
        QString mFiletypeTemplate;
        QString mFixTemplate;

    private:
        int SaveToFile(const QString& filename);
        QString guessFilenameStem();
};


class BashRemediationSaver : public RemediationSaverBase
{
    public:
	BashRemediationSaver(QWidget* parentWindow, ScanningSession* session):RemediationSaverBase(parentWindow, session)
	{
	    mSaveMessage = QObject::tr("Save remediation role as a bash script");
	    mFiletypeExtension = "sh";
	    mFiletypeTemplate = QObject::tr("bash script (*.%1)");
	    mFixTemplate = QObject::tr("urn:xccdf:fix:script:sh");
        }
};


class AnsibleRemediationSaver : public RemediationSaverBase
{
    public:
	AnsibleRemediationSaver(QWidget* parentWindow, ScanningSession* session):RemediationSaverBase(parentWindow, session)
	{
	    mSaveMessage = QObject::tr("Save remediation role as an ansible playbook");
	    mFiletypeExtension = "yml";
	    mFiletypeTemplate = QObject::tr("ansible playbook (*.%1)");
	    mFixTemplate = QObject::tr("urn:xccdf:fix:script:ansible");
        }
};

#endif // SCAP_WORKBENCH_REMEDIATION_ROLE_SAVER_H_
