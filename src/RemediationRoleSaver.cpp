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
#include <QMessageBox>

#include "RemediationRoleSaver.h"
#include "DiagnosticsDialog.h"
#include "Utils.h"

extern "C"
{
#include <oscap_error.h>
#include <xccdf_benchmark.h>
#include <xccdf_policy.h>
#include <xccdf_session.h>
#include <ds_rds_session.h>
}



const QString bashSaveMessage = QObject::tr("Save remediation as a bash script");
const QString bashFiletypeExtension = "sh";
const QString bashFiletypeTemplate = QObject::tr("bash script (*.%1)");
const QString bashFixTemplate = QString("sh");

const QString ansibleSaveMessage = QObject::tr("Save remediation as an ansible playbook");
const QString ansibleFiletypeExtension = "yml";
const QString ansibleFiletypeTemplate = QObject::tr("ansible playbook (*.%1)");
const QString ansibleFixType = QString("ansible");

const QString puppetSaveMessage = QObject::tr("Save remediation as a puppet manifest");
const QString puppetFiletypeExtension = "pp";
const QString puppetFiletypeTemplate = QObject::tr("puppet manifest (*.%1)");
const QString puppetFixType = QString("puppet");


RemediationSaverBase::RemediationSaverBase(QWidget* parentWindow,
                const QString& saveMessage, const QString& filetypeExtension, const QString& filetypeTemplate, const QString& fixType):
    mParentWindow(parentWindow), mDiagnostics(globalDiagnosticsDialog), mSaveMessage(saveMessage), mFiletypeExtension(filetypeExtension), mFiletypeTemplate(filetypeTemplate),
    mTemplateString(QString("urn:xccdf:fix:script:%1").arg(fixType))
{}

void RemediationSaverBase::selectFilenameAndSaveRole()
{
    const QString filename = QFileDialog::getSaveFileName(mParentWindow,
        mSaveMessage.toUtf8(),
        QString("%1.%2").arg(guessFilenameStem(), mFiletypeExtension),
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

void RemediationSaverBase::removeFileWhenEmpty(const QString& filename)
{
    QFile outputFile(filename);
    outputFile.open(QIODevice::ReadOnly);
    int fileSize = outputFile.size();
    outputFile.close();

    if (fileSize == 0)
        QFile::remove(filename);
}

void RemediationSaverBase::saveFileOK(const QString& filename)
{
    QMessageBox::information(
        mParentWindow, QObject::tr("SCAP Workbench"),
        QObject::tr("Success saving file: %1").arg(filename)
    );
}

void RemediationSaverBase::saveFileError(const QString& filename, const QString& errorMsg)
{
    removeFileWhenEmpty(filename);
    const QString completeErrorMessage = QObject::tr("Error generating remediation '%2': %1").arg(errorMsg, filename);
    mDiagnostics->errorMessage(completeErrorMessage);
}

QString RemediationSaverBase::guessFilenameStem() const
{
    // TODO: Add guess that uses benchmark and profile names
    return QString("remediation");
}

ProfileBasedRemediationSaver::ProfileBasedRemediationSaver(QWidget* parentWindow, ScanningSession* session,
        const QString& saveMessage, const QString& filetypeExtension, const QString& filetypeTemplate, const QString& fixType):
    RemediationSaverBase(parentWindow, saveMessage, filetypeExtension, filetypeTemplate, fixType), mScanningSession(session)
{}

void ProfileBasedRemediationSaver::saveToFile(const QString& filename)
{
    QFile outputFile(filename);
    outputFile.open(QIODevice::WriteOnly);
    struct xccdf_session* session = mScanningSession->getXCCDFSession();
    struct xccdf_policy* policy = xccdf_session_get_xccdf_policy(session);
    const int result = xccdf_policy_generate_fix(policy, NULL, mTemplateString.toUtf8().constData(), outputFile.handle());
    if (!outputFile.flush())
    {
        throw std::runtime_error("Could not write to the destination location.");
    }
    outputFile.close();
    if (result != 0)
    {
        const char* err = oscap_err_desc();
        if (err == NULL)
            err = "Unknown error";
        throw std::runtime_error(err);
    }
}

BashProfileRemediationSaver::BashProfileRemediationSaver(QWidget* parentWindow, ScanningSession* session):
    ProfileBasedRemediationSaver(parentWindow, session,
            bashSaveMessage, bashFiletypeExtension, bashFiletypeTemplate, bashFixTemplate)
{}

AnsibleProfileRemediationSaver::AnsibleProfileRemediationSaver(QWidget* parentWindow, ScanningSession* session):
    ProfileBasedRemediationSaver(parentWindow, session,
            ansibleSaveMessage, ansibleFiletypeExtension, ansibleFiletypeTemplate, ansibleFixType)
{}

PuppetProfileRemediationSaver::PuppetProfileRemediationSaver(QWidget* parentWindow, ScanningSession* session):
    ProfileBasedRemediationSaver(parentWindow, session,
            puppetSaveMessage, puppetFiletypeExtension, puppetFiletypeTemplate, puppetFixType)
{}

ResultBasedLibraryRemediationSaver::ResultBasedLibraryRemediationSaver(
        QWidget* parentWindow, const QByteArray& arfContents, const QString& tailoringFilePath,
        const QString& saveMessage, const QString& filetypeExtension, const QString& filetypeTemplate, const QString& fixType):
    RemediationSaverBase(parentWindow, saveMessage, filetypeExtension, filetypeTemplate, fixType)
{
    mArfFile.setAutoRemove(true);
    mArfFile.open();
    mArfFile.write(arfContents);
    mArfFile.close();
    tailoring = tailoringFilePath;
}

void ResultBasedLibraryRemediationSaver::saveToFile(const QString& filename)
{
    struct oscap_source* source = oscap_source_new_from_file(mArfFile.fileName().toUtf8().constData());
    oscap_document_type_t document_type = oscap_source_get_scap_type(source);
    if (document_type != OSCAP_DOCUMENT_ARF)
    {
        throw std::runtime_error("Expected an ARF file");
    }

    struct ds_rds_session* arf_session = ds_rds_session_new_from_source(source);
    if (arf_session == NULL)
    {
        throw std::runtime_error("Couldn't open ARF session");
    }
    struct oscap_source* report_source = ds_rds_session_select_report(arf_session, NULL);
    if (report_source == NULL)
    {
        throw std::runtime_error("Couldn't get report source from the ARF session");
    }
    struct oscap_source* report_request_source = ds_rds_session_select_report_request(arf_session, NULL);
    if (report_request_source == NULL)
    {
        throw std::runtime_error("Couldn't get report request source from the ARF session");
    }

    struct xccdf_session* session = xccdf_session_new_from_source(oscap_source_clone(report_request_source));
    if (xccdf_session_add_report_from_source(session, oscap_source_clone(report_source)))
    {
        throw std::runtime_error("Couldn't get report request source from the ARF session");
    }
    oscap_source_free(source);

    if (session == NULL)
        throw std::runtime_error("Couldn't get XCCDF session from the report source");
    if (!tailoring.isNull()) {
        xccdf_session_set_user_tailoring_file(session, tailoring.toUtf8().constData());
    }

    xccdf_session_set_loading_flags(session, XCCDF_SESSION_LOAD_XCCDF);
    if (xccdf_session_load(session) != 0)
        throw std::runtime_error("Couldn't load XCCDF");

    // "" for profile should work, as it works when passed to the command-line oscap
    if (xccdf_session_build_policy_from_testresult(session, "") != 0)
        throw std::runtime_error("Couldn't get build policy from testresult");

    struct xccdf_policy* policy = xccdf_session_get_xccdf_policy(session);
    struct xccdf_result* result = xccdf_policy_get_result_by_id(policy, xccdf_session_get_result_id(session));
    /* Result-oriented fixes */

    QFile outputFile(filename);
    outputFile.open(QIODevice::WriteOnly);

    const int rc = xccdf_policy_generate_fix(policy, result, mTemplateString.toUtf8().constData(), outputFile.handle());
    if (!outputFile.flush())
    {
        throw std::runtime_error("Could not write to the destination location.");
    }
    outputFile.close();
    ds_rds_session_free(arf_session);
    xccdf_session_free(session);

    if (rc != 0)
    {
        const char* err = oscap_err_desc();
        if (err == NULL)
            err = "Unknown error";
        throw std::runtime_error(err);
    }
}

BashResultRemediationSaver::BashResultRemediationSaver(QWidget* parentWindow, const QByteArray& arfContents, const QString& tailoringFilePath):
    ResultBasedLibraryRemediationSaver(parentWindow, arfContents, tailoringFilePath,
            bashSaveMessage, bashFiletypeExtension, bashFiletypeTemplate, bashFixTemplate)
{}

AnsibleResultRemediationSaver::AnsibleResultRemediationSaver(QWidget* parentWindow, const QByteArray& arfContents, const QString& tailoringFilePath):
    ResultBasedLibraryRemediationSaver(parentWindow, arfContents, tailoringFilePath,
            ansibleSaveMessage, ansibleFiletypeExtension, ansibleFiletypeTemplate, ansibleFixType)
{}

PuppetResultRemediationSaver::PuppetResultRemediationSaver(QWidget* parentWindow, const QByteArray& arfContents, const QString& tailoringFilePath):
    ResultBasedLibraryRemediationSaver(parentWindow, arfContents, tailoringFilePath,
            puppetSaveMessage, puppetFiletypeExtension, puppetFiletypeTemplate, puppetFixType)
{}

