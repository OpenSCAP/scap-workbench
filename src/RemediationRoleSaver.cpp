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
#ifdef SCAP_WORKBENCH_USE_LIBRARY_FOR_RESULT_BASED_REMEDIATION_ROLES_GENERATION
    // vvv This include is used only for library-based generation of result-base remediation roles
    // vvv and it requires (relatively recent) openscap 1.2.16
#include <ds_rds_session.h>
#endif
}

#include "TemporaryDir.h"
#include "RemediationRoleSaver.h"


QString bashSaveMessage = QObject::tr("Save remediation role as a bash script");
QString bashFiletypeExtension = "sh";
QString bashFiletypeTemplate = QObject::tr("bash script (*.%1)");
// template in liboscap for Bash is 'sh', whereas the oscap CLI knows of fix type 'bash'
QString bashFixTemplate = QString("sh");
QString bashFixType = QString("bash");

QString ansibleSaveMessage = QObject::tr("Save remediation role as an ansible playbook");
QString ansibleFiletypeExtension = "yml";
QString ansibleFiletypeTemplate = QObject::tr("ansible playbook (*.%1)");
QString ansibleFixType = QString("ansible");

QString puppetSaveMessage = QObject::tr("Save remediation role as a puppet manifest");
QString puppetFiletypeExtension = "pp";
QString puppetFiletypeTemplate = QObject::tr("puppet manifest (*.%1)");
QString puppetFixType = QString("puppet");


RemediationSaverBase::RemediationSaverBase(QWidget* parentWindow,
                const QString& saveMessage, const QString& filetypeExtension, const QString& filetypeTemplate, const QString& fixType):
    mParentWindow(parentWindow), mSaveMessage(saveMessage), mFiletypeExtension(filetypeExtension), mFiletypeTemplate(filetypeTemplate), mFixType(fixType)
{}


void RemediationSaverBase::selectFilenameAndSaveRole()
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


void RemediationSaverBase::saveFileOK(const QString& filename)
{
    // TODO: if OK - inform the user
}


void RemediationSaverBase::saveFileError(const QString& filename, const QString& error_msg)
{
    // TODO: if not OK - show error message
    std::cerr << QObject::tr("Error saving remediation role: %1\n").arg(error_msg).toUtf8().constData();
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
    QString role_template("urn:xccdf:fix:script:%1");
    role_template = role_template.arg(mFixType);
    const int result = xccdf_policy_generate_fix(policy, NULL, role_template.toUtf8().constData(), outputFile.handle());
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


#ifndef SCAP_WORKBENCH_USE_LIBRARY_FOR_RESULT_BASED_REMEDIATION_ROLES_GENERATION
ResultBasedProcessRemediationSaver::ResultBasedProcessRemediationSaver(QWidget* parentWindow, const QByteArray& arfContents,
        const QString& saveMessage, const QString& filetypeExtension, const QString& filetypeTemplate, const QString& fixType):
    RemediationSaverBase(parentWindow, saveMessage, filetypeExtension, filetypeTemplate, fixType), mParentWindow(parentWindow)
{
    mArfFile.setAutoRemove(true);
    mArfFile.open();
    mArfFile.write(arfContents);
    mArfFile.close();
}


void ResultBasedProcessRemediationSaver::saveToFile(const QString& filename)
{
    QStringList args;
    args.append("xccdf");
    args.append("generate");
    args.append("fix");

    args.append("--fix-type");
    args.append(mFixType);
    args.append("--output");
    args.append(filename);

    // vvv This will work, if there is only one result ID in the ARF file, it will be picked no matter what the argument value is.
    // However, ommitting --result-id "" won't work.
    args.append("--result-id");
    args.append("");

    args.append(mArfFile.fileName());

    // TODO: Launching a process and going through its output is something we do already
    // This is a lightweight launch though.
    QProcess process(RemediationSaverBase::mParentWindow);

    TemporaryDir workingDir;
    process.setWorkingDirectory(workingDir.getPath());
    QString program(SCAP_WORKBENCH_LOCAL_OSCAP_PATH);

    process.start(program, args);
    process.waitForStarted();

    const unsigned int pollInterval = 100;

    while (!process.waitForFinished(pollInterval))
    {}
    if (process.exitCode() == 1)
    {
        throw std::runtime_error(QObject::tr("There was an error in course of remediation role generation! Exit code of the 'oscap' process was 1.").toUtf8().constData());
    }
}


BashResultRemediationSaver::BashResultRemediationSaver(QWidget* parentWindow, const QByteArray& arfContents):
    ResultBasedProcessRemediationSaver(parentWindow, arfContents,
            bashSaveMessage, bashFiletypeExtension, bashFiletypeTemplate, bashFixType)
{}


AnsibleResultRemediationSaver::AnsibleResultRemediationSaver(QWidget* parentWindow, const QByteArray& arfContents):
    ResultBasedProcessRemediationSaver(parentWindow, arfContents,
            ansibleSaveMessage, ansibleFiletypeExtension, ansibleFiletypeTemplate, ansibleFixType)
{}


PuppetResultRemediationSaver::PuppetResultRemediationSaver(QWidget* parentWindow, const QByteArray& arfContents):
    ResultBasedProcessRemediationSaver(parentWindow, arfContents,
            puppetSaveMessage, puppetFiletypeExtension, puppetFiletypeTemplate, puppetFixType)
{}


#else  // i.e. SCAP_WORKBENCH_USE_LIBRARY_FOR_RESULT_BASED_REMEDIATION_ROLES_GENERATION is defined
ResultBasedLibraryRemediationSaver::ResultBasedLibraryRemediationSaver(QWidget* parentWindow, const QByteArray& arfContents,
        const QString& saveMessage, const QString& filetypeExtension, const QString& filetypeTemplate, const QString& fixType):
    RemediationSaverBase(parentWindow, saveMessage, filetypeExtension, filetypeTemplate, fixType)
{
    mArfFile.setAutoRemove(true);
    mArfFile.open();
    mArfFile.write(arfContents);
    mArfFile.close();
}


void ResultBasedLibraryRemediationSaver::saveToFile(const QString& filename)
{
    struct oscap_source* source = oscap_source_new_from_file(mArfFile.fileName().toUtf8().constData());
    oscap_document_type_t document_type = oscap_source_get_scap_type(source);
    if (document_type != OSCAP_DOCUMENT_ARF) {
        throw std::runtime_error("Expected an ARF file");
    }

    struct ds_rds_session* arf_session = ds_rds_session_new_from_source(source);
    if (arf_session == NULL) {
        throw std::runtime_error("Couldn't open ARF session");
    }
    struct oscap_source *report_source = ds_rds_session_select_report(arf_session, NULL);
    if (report_source == NULL) {
        throw std::runtime_error("Couldn't get report source from the ARF session");
    }
    struct oscap_source *report_request_source = ds_rds_session_select_report_request(arf_session, NULL);
    if (report_request_source == NULL) {
        throw std::runtime_error("Couldn't get report request source from the ARF session");
    }

    struct xccdf_session* session = xccdf_session_new_from_source(oscap_source_clone(report_request_source));
    if (xccdf_session_add_report_from_source(session, oscap_source_clone(report_source))) {
        throw std::runtime_error("Couldn't get report request source from the ARF session");
    }
    oscap_source_free(source);

    if (session == NULL)
        throw std::runtime_error("Couldn't get XCCDF session from the report source");

    xccdf_session_set_loading_flags(session, XCCDF_SESSION_LOAD_XCCDF);
    if (xccdf_session_load(session) != 0)
        throw std::runtime_error("Couldn't load XCCDF");

    // "" for profile should work, as it works when passed to the command-line oscap
    if (xccdf_session_build_policy_from_testresult(session, "") != 0)
        throw std::runtime_error("Couldn't get build policy from testresult");

    struct xccdf_policy* policy = xccdf_session_get_xccdf_policy(session);
    struct xccdf_result* result = xccdf_policy_get_result_by_id(policy, xccdf_session_get_result_id(session));
    /* Result-oriented fixes */

    QString role_template("urn:xccdf:fix:script:%1");
    role_template = role_template.arg(mFixType);

    QFile outputFile(filename);
    outputFile.open(QIODevice::WriteOnly);

    const int rc = xccdf_policy_generate_fix(policy, result, role_template.toUtf8().constData(), outputFile.handle());
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


BashResultRemediationSaver::BashResultRemediationSaver(QWidget* parentWindow, const QByteArray& arfContents):
    ResultBasedLibraryRemediationSaver(parentWindow, arfContents,
            bashSaveMessage, bashFiletypeExtension, bashFiletypeTemplate, bashFixTemplate)
{}


AnsibleResultRemediationSaver::AnsibleResultRemediationSaver(QWidget* parentWindow, const QByteArray& arfContents):
    ResultBasedLibraryRemediationSaver(parentWindow, arfContents,
            ansibleSaveMessage, ansibleFiletypeExtension, ansibleFiletypeTemplate, ansibleFixType)
{}


PuppetResultRemediationSaver::PuppetResultRemediationSaver(QWidget* parentWindow, const QByteArray& arfContents):
    ResultBasedLibraryRemediationSaver(parentWindow, arfContents,
            puppetSaveMessage, puppetFiletypeExtension, puppetFiletypeTemplate, puppetFixType)
{}

#endif  // SCAP_WORKBENCH_USE_LIBRARY_FOR_RESULT_BASED_REMEDIATION_ROLES_GENERATION
