/*
 * Copyright 2017 Red Hat Inc., Durham, North Carolina.
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
 *      Matej Tyc <matyc@redhat.com>
 */

#include <stdexcept>
#include <iostream>

#include <QFile>

extern "C"
{
#include <oscap_error.h>
#include <xccdf_benchmark.h>
#include <xccdf_policy.h>
#include <xccdf_session.h>
}

#include "RemediationRoleSaver.h"


template <QString* saveMessage, QString* filetypeExtension, QString* filetypeTemplate, QString* fixType>
RemediationSaverBase<saveMessage, filetypeExtension, filetypeTemplate, fixType>::RemediationSaverBase(QWidget* parentWindow):
    mParentWindow(parentWindow), mSaveMessage(*saveMessage), mFiletypeExtension(*filetypeExtension), mFiletypeTemplate(*filetypeTemplate), mFixType(*fixType)
{}


template <QString* saveMessage, QString* filetypeExtension, QString* filetypeTemplate, QString* fixType>
void RemediationSaverBase<saveMessage, filetypeExtension, filetypeTemplate, fixType>::selectFilenameAndSaveRole()
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

    try {
        saveToFile(filename);
        saveFileOK(filename);
    }
    catch (std::exception& exc)
    {
        saveFileError(filename, QString::fromUtf8(exc.what()));
    }
}


template <QString* saveMessage, QString* filetypeExtension, QString* filetypeTemplate, QString* fixType>
void RemediationSaverBase<saveMessage, filetypeExtension, filetypeTemplate, fixType>::saveFileOK(const QString& filename)
{
    // TODO: if OK - inform the user
}


template <QString* saveMessage, QString* filetypeExtension, QString* filetypeTemplate, QString* fixType>
void RemediationSaverBase<saveMessage, filetypeExtension, filetypeTemplate, fixType>::saveFileError(const QString& filename, const QString& error_msg)
{
    // TODO: if not OK - show error message
    std::cerr << QObject::tr("Error saving remediation role: %1\n").arg(error_msg).toUtf8().constData();
}


template <QString* saveMessage, QString* filetypeExtension, QString* filetypeTemplate, QString* fixType>
QString RemediationSaverBase<saveMessage, filetypeExtension, filetypeTemplate, fixType>::guessFilenameStem() const
{
    // TODO: Add guess that uses benchmark and profile names
    return QString("remediation");
}


template <QString* saveMessage, QString* filetypeExtension, QString* filetypeTemplate, QString* fixType>
ProfileBasedRemediationSaver<saveMessage, filetypeExtension, filetypeTemplate, fixType>::ProfileBasedRemediationSaver(QWidget* parentWindow, ScanningSession* session):
    RemediationSaverBase<saveMessage, filetypeExtension, filetypeTemplate, fixType>(parentWindow), mScanningSession(session)
{}


template <QString* saveMessage, QString* filetypeExtension, QString* filetypeTemplate, QString* fixType>
void ProfileBasedRemediationSaver<saveMessage, filetypeExtension, filetypeTemplate, fixType>::saveToFile(const QString& filename)
{
    QFile outputFile(filename);
    outputFile.open(QIODevice::WriteOnly);
    struct xccdf_session* session = mScanningSession->getXCCDFSession();
    struct xccdf_policy* policy = xccdf_session_get_xccdf_policy(session);
    QString role_template("urn:xccdf:fix:script:%1");
    role_template = role_template.arg(RemediationSaverBase<saveMessage, filetypeExtension, filetypeTemplate, fixType>::mFixType);
    int result = xccdf_policy_generate_fix(policy, NULL, RemediationSaverBase<saveMessage, filetypeExtension, filetypeTemplate, fixType>::mFixType.toUtf8(), outputFile.handle());
    outputFile.close();
    if (result != 0)
    {
        const char* err = oscap_err_desc();
        if (err == NULL)
            err = "Unknown error";
        throw std::runtime_error(err);
    }
}


template <QString* saveMessage, QString* filetypeExtension, QString* filetypeTemplate, QString* fixType>
ResultBasedRemediationSaver<saveMessage, filetypeExtension, filetypeTemplate, fixType>::ResultBasedRemediationSaver(QWidget* parentWindow, OscapScannerLocal* scanner):
    RemediationSaverBase<saveMessage, filetypeExtension, filetypeTemplate, fixType>(parentWindow), mScanner(scanner)
{}


template <QString* saveMessage, QString* filetypeExtension, QString* filetypeTemplate, QString* fixType>
void ResultBasedRemediationSaver<saveMessage, filetypeExtension, filetypeTemplate, fixType>::saveToFile(const QString& filename)
{
    if (mScanner == NULL)
    {
        std::cerr << QObject::tr("The scan was not a local one, so we can't generate local remediations.\n").toUtf8().constData();
        return;
    }
    mScanner->createRemediationRoleAfterEvaluate(RemediationSaverBase<saveMessage, filetypeExtension, filetypeTemplate, fixType>::mFixType, filename);
}
