/*
 * Copyright 2013 Red Hat Inc., Durham, North Carolina.
 * All Rights Reserved.
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.
 *
 * Authors:
 *      Martin Preisler <mpreisle@redhat.com>
 */

#include "RemediationRoleSaver.h"

void RemediationSaverBase::SelectFilenameAndSaveRole()
{
    const QString filename = QFileDialog::getSaveFileName(mParentWindow,
        mSaveMessage.toUtf8(),
        QString("%1.%2").arg(guessFilenameStem()).arg(mFiletypeExtension),
        mFiletypeTemplate.arg(mFiletypeExtension), 0
#ifndef SCAP_WORKBENCH_USE_NATIVE_FILE_DIALOGS
        , QFileDialog::DontUseNativeDialog
#endif
    );

    if (filename.isEmpty())
        return;

    int result = SaveToFile(filename);
    if (result == 0)
    {
        // TODO: if OK
    }
    else
    {
        // TODO: if not OK
    }
}

int RemediationSaverBase::SaveToFile(const QString& filename)
{
    QFile outputFile(filename);
    outputFile.open(QIODevice::WriteOnly);
    struct xccdf_session* session = mScanningSession->getXCCDFSession();
    struct xccdf_policy* policy = xccdf_session_get_xccdf_policy(session);
    int result = xccdf_policy_generate_fix(policy, NULL, mFixTemplate.toUtf8(), outputFile.handle());
    outputFile.close();
    return result;
}

QString RemediationSaverBase::guessFilenameStem()
{
    // TODO: Add guess that uses benchmark and profile names
    return QString("remediation");
}


BashRemediationSaver::BashRemediationSaver(QWidget* parentWindow, ScanningSession* session):RemediationSaverBase(parentWindow, session)
{
    mSaveMessage = QObject::tr("Save remediation role as a bash script");
    mFiletypeExtension = "sh";
    mFiletypeTemplate = QObject::tr("bash script (*.%1)");
    mFixTemplate = QObject::tr("urn:xccdf:fix:script:sh");
}


AnsibleRemediationSaver::AnsibleRemediationSaver(QWidget* parentWindow, ScanningSession* session):RemediationSaverBase(parentWindow, session)
{
    mSaveMessage = QObject::tr("Save remediation role as an ansible playbook");
    mFiletypeExtension = "yml";
    mFiletypeTemplate = QObject::tr("ansible playbook (*.%1)");
    mFixTemplate = QObject::tr("urn:xccdf:fix:script:ansible");
}
