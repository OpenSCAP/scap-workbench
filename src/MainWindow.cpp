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

#include "MainWindow.h"
#include "OscapScannerLocal.h"
#include "OscapScannerRemoteSsh.h"
#include "ResultViewer.h"
#include "DiagnosticsDialog.h"
#include "CommandLineArgsDialog.h"
#include "TailorProfileDialog.h"
#include "TailoringWindow.h"
#include "ScanningSession.h"
#include "Exceptions.h"
#include "APIHelpers.h"
#include "SaveAsRPMDialog.h"
#include "RPMOpenHelper.h"
#include "Utils.h"
#include "SSGIntegrationDialog.h"

#include <QFileDialog>
#include <QAbstractEventDispatcher>
#include <QCloseEvent>
#include <QDesktopWidget>

#include <cassert>
#include <set>

extern "C" {
#include <xccdf_policy.h>
#include <xccdf_session.h>
#include <scap_ds.h>
}

// A dialog to open a tailoring file is displayed after user selects this option
// from the tailoring combobox.
const QString TAILORING_CUSTOM_FILE = QObject::tr("Select customization file...");
// This option signifies that there is no tailoring being done and the plain
// content file is used, it also resets tailoring when selected.
const QString TAILORING_NONE = QObject::tr("None selected");
// Signifies that tailoring changes have been made and have not been saved
// to a file (yet?). Selecting it does nothing.
const QString TAILORING_UNSAVED = QObject::tr("(unsaved changes)");

// Magic string that we use to distinguish that we have no loaded tailoring file
// in the tailoring combobox.
const QVariant TAILORING_NO_LOADED_FILE_DATA = "&*&()@#$(no loaded file)";

MainWindow::MainWindow(QWidget* parent):
    QMainWindow(parent),

    mQSettings(new QSettings(this)),

    mDiagnosticsDialog(0),
    mCommandLineArgsDialog(0),

    mRPMOpenHelper(0),
    mSkipValid(false),
    mScanningSession(0),

    mScanThread(0),
    mScanner(0),

    mOldTailoringComboBoxIdx(0),
    mLoadedTailoringFileUserData(TAILORING_NO_LOADED_FILE_DATA),

    mIgnoreProfileComboBox(false),

    mRuleResultsExpanded(false)
{
    mUI.setupUi(this);
    mUI.progressBar->reset();

    // we start with localhost which doesn't need remote machine details
    mUI.remoteMachineDetails->hide();

    QObject::connect(
        mUI.expandRulesButton, SIGNAL(clicked()),
        this, SLOT(toggleRuleResultsExpanded())
    );

    QObject::connect(
        this, SIGNAL(closeMainWindow()),
        this, SLOT(close()),
        // Queued to prevent closing the MainWindow before event loop is
        // entered. Without this the application wouldn't quit gracefully.
        Qt::QueuedConnection
    );

    QObject::connect(
        this, SIGNAL(showOpenFileDialog()),
        this, SLOT(openFileDialog()),
        // Queued to prevent opening a blocking dialog before event loop is
        // entered. Without this the application wouldn't quit gracefully.
        Qt::QueuedConnection
    );
    QObject::connect(
        mUI.actionOpen, SIGNAL(triggered()),
        this, SLOT(openFileDialog())
    );
    QObject::connect(
        mUI.actionOpenSSG, SIGNAL(triggered()),
        this, SLOT(openSSGDialog())
    );
    QObject::connect(
        mUI.actionOpenCustomizationFile, SIGNAL(triggered()),
        this, SLOT(openCustomizationFile())
    );
    QObject::connect(
        mUI.checklistComboBox, SIGNAL(currentIndexChanged(int)),
        this, SLOT(checklistComboboxChanged(int))
    );
    QObject::connect(
        mUI.tailoringFileComboBox, SIGNAL(currentIndexChanged(int)),
        this, SLOT(tailoringFileComboboxChanged(int))
    );
    QObject::connect(
        mUI.profileComboBox, SIGNAL(currentIndexChanged(int)),
        this, SLOT(profileComboboxChanged(int))
    );
#ifndef SCAP_WORKBENCH_LOCAL_SCAN_ENABLED
    mUI.localMachineRadioButton->setEnabled(false);
    mUI.localMachineRadioButton->setToolTip(
        QObject::tr("SCAP Workbench was compiled without local scanning support")
    );
    mUI.localMachineRadioButton->setChecked(false);
# ifdef SCAP_WORKBENCH_LOCAL_SSH_FOUND
    mUI.remoteMachineRadioButton->setChecked(true);
# endif
#endif

#ifndef SCAP_WORKBENCH_LOCAL_SSH_FOUND
    mUI.remoteMachineRadioButton->setEnabled(false);
    mUI.remoteMachineRadioButton->setToolTip(
        QObject::tr("SCAP Workbench was compiled without remote scanning support")
    );
#endif

#ifndef SCAP_WORKBENCH_LOCAL_SCAN_ENABLED
# ifndef SCAP_WORKBENCH_LOCAL_SSH_FOUND
    // no scanning is possible, not remote, not local
    mUI.scanButton->setEnabled(false);
    mUI.scanButton->setToolTip(
        QObject::tr("SCAP Workbench was compiled without local and remote scanning support. Only tailoring is possible.")
    );
# endif
#endif

    QObject::connect(
        mUI.scanButton, SIGNAL(clicked()),
        this, SLOT(scanAsyncAutoMode())
    );
    QObject::connect(
        mUI.offlineRemediateButton, SIGNAL(clicked()),
        this, SLOT(offlineRemediateAsync())
    );
    QObject::connect(
        mUI.cancelButton, SIGNAL(clicked()),
        this, SLOT(cancelScanAsync())
    );
    QObject::connect(
        mUI.clearButton, SIGNAL(clicked()),
        this, SLOT(clearResults())
    );

    QObject::connect(
        mUI.actionSaveIntoDirectory, SIGNAL(triggered()),
        this, SLOT(saveIntoDirectory())
    );
#ifdef SCAP_WORKBENCH_LOCAL_SCAP_AS_RPM_FOUND
        QObject::connect(
            mUI.actionSaveAsRPM, SIGNAL(triggered()),
            this, SLOT(saveAsRPM())
        );
#else
        mUI.actionSaveAsRPM->setEnabled(false);
        mUI.actionSaveAsRPM->setToolTip("SCAP Workbench was compiled without Save as RPM support");
#endif

    QObject::connect(
        mUI.customizeProfileButton, SIGNAL(clicked()),
        this, SLOT(customizeProfile())
    );

    QObject::connect(
        mUI.actionSaveTailoring, SIGNAL(triggered()),
        this, SLOT(saveTailoring())
    );

    QObject::connect(
        mUI.showGuideButton, SIGNAL(released()),
        this, SLOT(showGuide())
    );

    QObject::connect(
        mUI.actionUserManual, SIGNAL(triggered()),
        this, SLOT(showUserManual())
    );

    mDiagnosticsDialog = new DiagnosticsDialog(this);
    mDiagnosticsDialog->hide();

    mCommandLineArgsDialog = new CommandLineArgsDialog(this);
    mCommandLineArgsDialog->hide();

    QObject::connect(
        mUI.actionShowDiagnostics, SIGNAL(triggered()),
        mDiagnosticsDialog, SLOT(show())
    );

    QObject::connect(
        mUI.actionAbout, SIGNAL(triggered()),
        this, SLOT(about())
    );
    QObject::connect(
        mUI.actionAboutQt, SIGNAL(triggered()),
        this, SLOT(aboutQt())
    );

    // FIXME: This is hidden to avoid people trying to use it when it is still
    //        not supported in openscap.
    mUI.offlineRemediateButton->hide();
    // FIXME: Hidden because tailoring isn't taken into account, this needs support
    //        in openscap first.
    mUI.showGuideButton->hide();

    mScanningSession = new ScanningSession();

    closeFile();

    // start centered
    move(QApplication::desktop()->screen()->rect().center() - rect().center());
}

MainWindow::~MainWindow()
{
    delete mScanner;
    mScanner = 0;

    closeFile();

    delete mScanningSession;
    mScanningSession = 0;

    delete mQSettings;
    mQSettings = 0;
}

void MainWindow::setSkipValid(bool skipValid)
{
    mSkipValid = skipValid;
}

void MainWindow::clearResults()
{
    mUI.scanProperties->setEnabled(true);

    mUI.scanTools->hide();
    mUI.scanTools->setEnabled(false);
    mUI.postScanTools->hide();
    mUI.postScanTools->setEnabled(false);
    mUI.preScanTools->show();
    mUI.preScanTools->setEnabled(true);

    mUI.resultViewer->clear();
    mUI.ruleResultsTree->clearResults();
    mUI.ruleResultsTree->setEnabled(true);

    statusBar()->clearMessage();

    if (mScanningSession && mScanningSession->fileOpened())
    {
        struct xccdf_policy* policy = xccdf_session_get_xccdf_policy(mScanningSession->getXCCDFSession());
        const int selected_rules = policy ? xccdf_policy_get_selected_rules_count(policy) : 0;
        mUI.progressBar->setRange(0, std::max(1, selected_rules));
        mUI.progressBar->setTextVisible(selected_rules > 0);
    }
    else
    {
        mUI.progressBar->setRange(0, 1);
        mUI.progressBar->setTextVisible(false);
    }

    mUI.progressBar->reset();
    mUI.progressBar->setValue(0);
    mUI.progressBar->setEnabled(true);

    mUI.menuSave->setEnabled(true);
    mUI.actionOpen->setEnabled(true);
}

void MainWindow::openFile(const QString& path)
{
    try
    {
        QString inputPath = path;
        QString tailoringPath = "";

        if (path.endsWith(".rpm"))
        {
            mRPMOpenHelper = new RPMOpenHelper(path);
            inputPath = mRPMOpenHelper->getInputPath();
            tailoringPath = mRPMOpenHelper->getTailoringPath();
        }

        mScanningSession->setSkipValid(mSkipValid);
        mScanningSession->openFile(inputPath);

        // In case openscap autonegotiated opening a tailoring file directly
        if (tailoringPath.isEmpty() && mScanningSession->hasTailoring())
            tailoringPath = inputPath;

        const QFileInfo pathInfo(path);
        setWindowTitle(QObject::tr("%1 - SCAP Workbench").arg(pathInfo.fileName()));

        mUI.tailoringFileComboBox->addItem(QString(TAILORING_NONE), QVariant(QString::Null()));
        mUI.tailoringFileComboBox->addItem(QString(TAILORING_CUSTOM_FILE), QVariant(QString::Null()));
        // we have just loaded the input file fresh, there are no tailoring changes to save
        markNoUnsavedTailoringChanges();

        refreshChecklists();

        if (!tailoringPath.isEmpty())
        {
            mScanningSession->setTailoringFile(tailoringPath);
            markLoadedTailoringFile(tailoringPath);
        }

        // force load up of the session
        checklistComboboxChanged(0);

        centralWidget()->setEnabled(true);

        mDiagnosticsDialog->infoMessage(QObject::tr("Opened file '%1'.").arg(path));
    }
    catch (const std::exception& e)
    {
        mScanningSession->closeFile();

        setWindowTitle(QObject::tr("SCAP Workbench"));
        mUI.tailoringFileComboBox->clear();

        mDiagnosticsDialog->exceptionMessage(e, QObject::tr("Error while opening file."), MF_PREFORMATTED_XML);
    }
}

void MainWindow::openFileDialog()
{
    // A diagnostic dialog might still be visible from previous failed openFile
    // that was called because of file passed on the command line.
    //
    // Do not continue until user dismisses the diagnostics dialog.
    mDiagnosticsDialog->waitUntilHidden();

    QString defaultDirectory = SCAP_WORKBENCH_SCAP_CONTENT_DIRECTORY;

    // can't use the default directory if it doesn't exist
    if (!QFileInfo(defaultDirectory).isDir())
        defaultDirectory = "";

    bool opened = false;
    while (!opened)
    {
        const QString path = QFileDialog::getOpenFileName(this,
            QObject::tr("Open Source DataStream or XCCDF file"),
            defaultDirectory,
            QObject::tr("Source DataStream, XCCDF file or SCAP RPM (*.xml *.xml.bz2 *.rpm);;All files (*)"), 0
#ifndef SCAP_WORKBENCH_USE_NATIVE_FILE_DIALOGS
            , QFileDialog::DontUseNativeDialog
#endif
        );

        if (path.isEmpty())
            // user cancelled the dialog, get out of this loop
            break;

        if (fileOpened())
        {
            if (openNewFileQuestionDialog(mScanningSession->getOpenedFilePath()) == QMessageBox::Yes)
                closeFile();
            else
                // user cancelled closing current file, we have to abort
                break;
        }

        openFile(path);

        if (!fileOpened())
        {
            // Error occurred, keep pumping events and don't move on until user
            // dismisses diagnostics dialog.
            mDiagnosticsDialog->waitUntilHidden();
        }
        else
            opened = true;
    }

    if (!fileOpened())
    {
        if (!close())
            throw MainWindowException("Failed to close main window!");
    }
}

void MainWindow::openSSGDialog(const QString& customDismissLabel)
{
    if (!SSGIntegrationDialog::isSSGAvailable())
        return;

    // A diagnostic dialog might still be visible from previous failed openFile
    // that was called because of file passed on the command line.
    //
    // Do not continue until user dismisses the diagnostics dialog.
    mDiagnosticsDialog->waitUntilHidden();

    SSGIntegrationDialog* dialog = new SSGIntegrationDialog(this);
    if (!customDismissLabel.isEmpty())
        dialog->setDismissLabel(customDismissLabel);

    if (dialog->exec() == QDialog::Accepted)
    {
        if (dialog->loadOtherContentSelected())
        {
            // don't worry about open files, the openFileDialog will ask if
            // user wants to close any open file
            openFileDialogAsync();
        }
        else
        {

            if (fileOpened())
            {
                if (openNewFileQuestionDialog(mScanningSession->getOpenedFilePath()) == QMessageBox::Yes)
                {
                    closeFile();
                }
                else
                {
                    // user cancelled closing current file, we have to abort
                    delete dialog;
                    return;
                }
            }
            openFile(dialog->getSelectedSSGFile());
        }
    }
    else
    {
        // User dissmissed SSGIntegrationDialog
        if (!fileOpened())
            closeMainWindowAsync();
    }

    delete dialog;
}

void MainWindow::closeMainWindowAsync()
{
    emit closeMainWindow();
}

void MainWindow::openFileDialogAsync()
{
    emit showOpenFileDialog();
}

bool MainWindow::fileOpened() const
{
    return mScanningSession && mScanningSession->fileOpened();
}

QString MainWindow::getOpenedFilePath() const
{
    if (fileOpened())
        return mScanningSession->getOpenedFilePath();

    return "";
}

void MainWindow::scanAsyncAutoMode()
{
    if (mUI.onlineRemediationCheckBox->checkState() == Qt::Checked)
        scanAsync(SM_SCAN_ONLINE_REMEDIATION);
    else
        scanAsync(SM_SCAN);
}

void MainWindow::scanAsync(ScannerMode scannerMode)
{
    assert(fileOpened());
    assert(!mScanThread);

    clearResults();

    if (mUI.ruleResultsTree->getSelectedRulesCount() == 0)
    {
        if (QMessageBox::question(this, QObject::tr("Scan with no rules selected?"),
                QObject::tr("Chosen profile does not have any rules selected. Are you sure you want to evaluate with no rules selected?"),
                QMessageBox::Yes | QMessageBox::No,
                QMessageBox::No) == QMessageBox::No)
        {
            return;
        }
    }

    mUI.scanProperties->setEnabled(false);
    mUI.preScanTools->hide();
    mUI.preScanTools->setEnabled(false);
    mUI.scanTools->show();
    mUI.scanTools->setEnabled(true);

    mUI.menuSave->setEnabled(false);
    mUI.actionOpen->setEnabled(false);

    mUI.ruleResultsTree->prepareForScanning();

    struct xccdf_policy* policy = xccdf_session_get_xccdf_policy(mScanningSession->getXCCDFSession());
    if (!policy)
    {
        mDiagnosticsDialog->errorMessage(QString(
            QObject::tr("Can't get XCCDF policy from the session. Very likely it failed to load. "
            "OpenSCAP error message:\n%1")).arg(oscapErrDesc()));

        mUI.scanProperties->setEnabled(true);
        mUI.scanTools->hide();
        mUI.scanTools->setEnabled(false);
        mUI.preScanTools->show();
        mUI.preScanTools->setEnabled(true);

        mUI.menuSave->setEnabled(true);
        mUI.actionOpen->setEnabled(true);

        return;
    }

    const int selected_rules = xccdf_policy_get_selected_rules_count(policy);
    mUI.progressBar->setRange(0, std::max(1, selected_rules));
    mUI.progressBar->reset();
    mUI.progressBar->setValue(0);
    mUI.progressBar->setEnabled(true);
    mUI.progressBar->setTextVisible(selected_rules > 0);
    mUI.ruleResultsTree->setEnabled(true);

    mScanThread = new QThread(this);

    // We pack the port to the end of target solely for the ease of comparing
    // targets (which can avoid reconnection and reauthentication).
    // In the OscapScannerRemoteSsh class the port will be parsed out again...
    const QString target = mUI.localMachineRadioButton->isChecked() ?
        "localhost" : mUI.remoteMachineDetails->getTarget();

    bool fetchRemoteResources = mUI.fetchRemoteResourcesCheckbox->isChecked();
    try
    {
        //if (!mScanner || mScanner->getTarget() != target)
        {
            delete mScanner;

            if (target == "localhost")
                mScanner = new OscapScannerLocal();
            else
                mScanner = new OscapScannerRemoteSsh();

            mScanner->setTarget(target);

            QObject::connect(
                this, SIGNAL(cancelScan()),
                mScanner, SLOT(cancel())
            );
            QObject::connect(
                mScanner, SIGNAL(progressReport(QString,QString)),
                this, SLOT(scanProgressReport(QString,QString))
            );
            QObject::connect(
                mScanner, SIGNAL(infoMessage(QString)),
                this, SLOT(scanInfoMessage(QString))
            );
            QObject::connect(
                mScanner, SIGNAL(warningMessage(QString)),
                this, SLOT(scanWarningMessage(QString))
            );
            QObject::connect(
                mScanner, SIGNAL(errorMessage(QString)),
                this, SLOT(scanErrorMessage(QString))
            );
            QObject::connect(
                mScanner, SIGNAL(canceled()),
                this, SLOT(scanCanceled())
            );
            QObject::connect(
                mScanner, SIGNAL(finished()),
                this, SLOT(scanFinished())
            );
        }

        mScanner->setScanThread(mScanThread);
        mScanner->setMainThread(thread());
        mScanner->setSkipValid(mSkipValid);
        mScanner->setFetchRemoteResources(fetchRemoteResources);
        mScanner->setSession(mScanningSession);
        mScanner->setScannerMode(scannerMode);

        if (scannerMode == SM_OFFLINE_REMEDIATION)
        {
            // TODO: Allow user to tweak the results to deselect/select rules to remediate, etc...
            mScanner->setARFForRemediation(mUI.resultViewer->getARF());
        }
    }
    catch (const std::exception& e)
    {
        scanCanceled();
        mDiagnosticsDialog->exceptionMessage(e, QObject::tr("There was a problem setting up the scanner."));
        return;
    }

    mScanner->moveToThread(mScanThread);

    mScanner->setDryRun(mUI.dryRunCheckBox->isChecked());
    if (mUI.dryRunCheckBox->isChecked())
    {
        const QStringList args = mScanner->getCommandLineArgs();
        mCommandLineArgsDialog->setArgs(args);
        mCommandLineArgsDialog->show();
    }

    QObject::connect(
        mScanThread, SIGNAL(started()),
        mScanner, SLOT(evaluateExceptionGuard())
    );

    if (target != "localhost")
        mUI.remoteMachineDetails->notifyTargetUsed(mScanner->getTarget());

    mScanThread->start();
}

void MainWindow::offlineRemediateAsync()
{
    scanAsync(SM_OFFLINE_REMEDIATION);
}

void MainWindow::cancelScanAsync()
{
    assert(fileOpened());

    mUI.cancelButton->setEnabled(false);
    emit cancelScan();
}

void MainWindow::enable()
{
    setEnabled(true);
}

void MainWindow::closeEvent(QCloseEvent* event)
{
    if (mScanThread)
    {
        if (QMessageBox::question(this, QObject::tr("Cancel scan in progress?"),
            QObject::tr("A scan is in progress. Are you sure you want to terminate it and close the application?"),
            QMessageBox::Yes | QMessageBox::No, QMessageBox::No) == QMessageBox::No)
        {
            event->ignore();
            return;
        }
    }

    if (fileOpened())
        cancelScanAsync();

    if (unsavedTailoringChanges())
    {
        if (QMessageBox::question(this, QObject::tr("Unsaved customization changes"),
            QObject::tr("There are unsaved customization changes, closing SCAP Workbench will destroy them. "
            "Are you sure you want to close and discard the changes?"),
            QMessageBox::Yes | QMessageBox::No, QMessageBox::No) == QMessageBox::No)
        {
            event->ignore();
            return;
        }
    }

    // wait until scanner cancels
    while (mScanThread != 0)
    {
        QAbstractEventDispatcher::instance(0)->processEvents(QEventLoop::AllEvents);
    }

    mDiagnosticsDialog->infoMessage(QObject::tr("Closing the main window..."));
    QMainWindow::closeEvent(event);
}

void MainWindow::closeFile()
{
    try
    {
        mScanningSession->closeFile();
    }
    catch (const std::exception& e)
    {
        // Have to reset scanning session to a sane state. This may leak
        // but is the best we can do right now.
        delete mScanningSession;
        mScanningSession = new ScanningSession();

        mDiagnosticsDialog->exceptionMessage(e, QObject::tr("Failed to close file."));
    }

    delete mRPMOpenHelper; mRPMOpenHelper = 0;

    centralWidget()->setEnabled(false);

    setWindowTitle(QObject::tr("SCAP Workbench"));

    mUI.checklistComboBox->clear();
    mUI.checklistComboBox->hide();
    mUI.checklistLabel->hide();

    mUI.tailoringFileComboBox->clear();

    mUI.profileComboBox->clear();

    clearResults();
}

void MainWindow::reloadSession()
{
    try
    {
        mScanningSession->reloadSession();
    }
    catch (const std::exception& e)
    {
        mDiagnosticsDialog->exceptionMessage(e);
    }

    mUI.resultViewer->clear();
    mUI.titleLabel->setText(mScanningSession->getBenchmarkTitle());
    toggleRuleResultsExpanded(false);
    refreshProfiles();
}

void MainWindow::notifyTailoringFinished(bool newProfile, bool changesConfirmed)
{
    if (newProfile && !changesConfirmed)
    {
        struct xccdf_session* session = mScanningSession->getXCCDFSession();
        struct xccdf_policy_model* pmodel = xccdf_session_get_policy_model(session);
        struct xccdf_tailoring* tailoring = xccdf_policy_model_get_tailoring(pmodel);
        assert(tailoring != 0);

        struct xccdf_profile* profile = xccdf_tailoring_get_profile_by_id(tailoring, mScanningSession->getProfile().toUtf8().constData());
        assert(profile != 0);
        xccdf_tailoring_remove_profile(tailoring, profile);
    }

    refreshProfiles();
    mUI.ruleResultsTree->refreshSelectedRules(mScanningSession);

    if (changesConfirmed)
        markUnsavedTailoringChanges();
}

void MainWindow::refreshProfiles()
{
    const int previousIndex = mUI.profileComboBox->currentIndex();
    const QString previouslySelected = previousIndex == -1 ?
        QString::Null() : mUI.profileComboBox->itemData(previousIndex).toString();

    mIgnoreProfileComboBox = true;

    mUI.profileComboBox->clear();

    if (!fileOpened())
        return;

    try
    {
        const std::map<QString, struct xccdf_profile*> profiles = mScanningSession->getAvailableProfiles();
        struct xccdf_policy_model* policyModel = xccdf_session_get_policy_model(mScanningSession->getXCCDFSession());

        // A nice side effect here is that profiles will be sorted by their IDs
        // because of the RB-tree implementation of std::map.
        for (std::map<QString, struct xccdf_profile*>::const_iterator it = profiles.begin();
             it != profiles.end(); ++it)
        {
            QString profileTitle = oscapTextIteratorGetPreferred(xccdf_profile_get_title(it->second));

            struct xccdf_policy* policy = xccdf_policy_new(policyModel, it->second);
            const int selectedRulesCount = xccdf_policy_get_selected_rules_count(policy);
            xccdf_policy_free(policy);

            profileTitle = profileTitle +" ("+ QString::number(selectedRulesCount) + ")";
            mUI.profileComboBox->addItem(profileTitle, QVariant(it->first));
        }

        if (previouslySelected != QString::Null())
        {
            const int indexCandidate = mUI.profileComboBox->findData(QVariant(previouslySelected));
            if (indexCandidate != -1)
                mUI.profileComboBox->setCurrentIndex(indexCandidate);
        }

        // default profile
        {
            QString profileTitle = QObject::tr("(default)");

            // We use QT_VERSION_CHECK to transform major, minor, patch numbers into
            // one easy comparable number.
            // We can only count selected rules for default profile if we are compiling against
            // OpenSCAP versions newer than 1.2.12.
            // See https://github.com/OpenSCAP/openscap/pull/607
#if (QT_VERSION_CHECK(OPENSCAP_VERSION_MAJOR, OPENSCAP_VERSION_MINOR, OPENSCAP_VERSION_PATCH) > QT_VERSION_CHECK(1, 2, 12))
            struct xccdf_policy* policy = xccdf_policy_new(policyModel, NULL);
            const int selectedRulesCount = xccdf_policy_get_selected_rules_count(policy);
            xccdf_policy_free(policy);

            profileTitle = profileTitle + " ("+ QString::number(selectedRulesCount) + ")";
#endif

            // Intentionally comes last. Users are more likely to use profiles other than (default)
#if (QT_VERSION >= QT_VERSION_CHECK(4, 4, 0))
            mUI.profileComboBox->insertSeparator(mUI.profileComboBox->count());
#endif
            mUI.profileComboBox->addItem(profileTitle, QVariant(QString::Null()));
        }
    }
    catch (const std::exception& e)
    {
        mUI.profileComboBox->clear();
        mDiagnosticsDialog->exceptionMessage(e, QObject::tr("Error while refreshing available XCCDF profiles."));
    }

    mIgnoreProfileComboBox = false;
    profileComboboxChanged(mUI.profileComboBox->currentIndex());
}

void MainWindow::refreshChecklists()
{
    try
    {
        mUI.checklistComboBox->clear();

        if (mScanningSession->isSDS())
        {
            struct ds_sds_index* sds_idx = xccdf_session_get_sds_idx(mScanningSession->getXCCDFSession());

            struct ds_stream_index_iterator* streams_it = ds_sds_index_get_streams(sds_idx);
            while (ds_stream_index_iterator_has_more(streams_it))
            {
                struct ds_stream_index* stream_idx = ds_stream_index_iterator_next(streams_it);
                const QString stream_id = QString::fromUtf8(ds_stream_index_get_id(stream_idx));

                struct oscap_string_iterator* checklists_it = ds_stream_index_get_checklists(stream_idx);
                while (oscap_string_iterator_has_more(checklists_it))
                {
                    const QString checklist_id = QString::fromUtf8(oscap_string_iterator_next(checklists_it));

                    QStringList data;
                    data.append(stream_id);
                    data.append(checklist_id);

                    mUI.checklistComboBox->addItem(QString("%1 / %2").arg(stream_id).arg(checklist_id), data);
                }
                oscap_string_iterator_free(checklists_it);
            }
            ds_stream_index_iterator_free(streams_it);

            mUI.checklistComboBox->setVisible(mUI.checklistComboBox->count() > 1);
            mUI.checklistLabel->setVisible(mUI.checklistComboBox->count() > 1);
        }
    }
    catch (...)
    {
        // do not leave the combobox partially filled
        mUI.checklistComboBox->clear();
        throw;
    }
}

void MainWindow::cleanupScanThread()
{
    if (mScanThread != 0)
    {
        mScanThread->wait();
        mScanThread->deleteLater();
        mScanThread = 0;
    }

    mUI.progressBar->setEnabled(false);
}

void MainWindow::checklistComboboxChanged(int index)
{
    if (!mScanningSession->isSDS())
        return;

    const QStringList data = mUI.checklistComboBox->itemData(index).toStringList();

    try
    {
        if (data.size() == 2)
        {
            mScanningSession->setDatastreamID(data.at(0));
            mScanningSession->setComponentID(data.at(1));
        }
        else
        {
            mScanningSession->setDatastreamID(QString());
            mScanningSession->setComponentID(QString());
        }

        reloadSession();
    }
    catch (const std::exception& e)
    {
        mDiagnosticsDialog->exceptionMessage(e);
    }
}

void MainWindow::tailoringFileComboboxChanged(int index)
{
    if (!fileOpened())
        return;

    const QString text = mUI.tailoringFileComboBox->itemText(index);
    const QVariant data = mUI.tailoringFileComboBox->itemData(index);

    bool tailoringLoaded = false;
    try
    {
        if (data.toString().isNull()) // Null data means it's an action
        {
            if (text == TAILORING_NONE) // resets tailoring
            {
                if (unsavedTailoringChanges())
                {
                    if (QMessageBox::question(this, QObject::tr("Unsaved customization changes!"),
                            QObject::tr("Are you sure you want to reset customization and wipe all unsaved changes?"),
                            QMessageBox::Yes | QMessageBox::No, QMessageBox::No) == QMessageBox::No)
                    {
                        mUI.tailoringFileComboBox->setCurrentIndex(mOldTailoringComboBoxIdx); // user canceled, set to previous value
                        return; // This prevents us from resetting mOldTailoringComboBoxIdx!
                    }
                }

                mScanningSession->resetTailoring();
                // tailoring has been reset, there are no tailoring changes to save
                markNoUnsavedTailoringChanges();
                // and the previously loaded tailoring file has to be removed from the combobox
                markRemoveLoadedTailoringFile();
            }
            else if (text == TAILORING_CUSTOM_FILE) // loads custom file
            {
                const QString filePath = QFileDialog::getOpenFileName(
                    this, QObject::tr("Open customization (XCCDF tailoring file)"), QString(),
                    QObject::tr("XCCDF tailoring file (*.xml *.xml.bz2)"), 0
#ifndef SCAP_WORKBENCH_USE_NATIVE_FILE_DIALOGS
                    , QFileDialog::DontUseNativeDialog
#endif
                );

                if (filePath.isEmpty())
                {
                    mUI.tailoringFileComboBox->setCurrentIndex(mOldTailoringComboBoxIdx); // user canceled, set to previous value
                    return; // This prevents us from resetting mOldTailoringComboBoxIdx!
                }
                else
                {
                    if (mScanningSession->hasTailoring() &&
                        QMessageBox::question(this, QObject::tr("Unsaved customization changes!"),
                            QObject::tr("Are you sure you want to load a customization file and wipe all unsaved changes?"),
                            QMessageBox::Yes | QMessageBox::No, QMessageBox::No) == QMessageBox::No)
                    {
                        mUI.tailoringFileComboBox->setCurrentIndex(mOldTailoringComboBoxIdx); // user canceled, set to previous value
                        return; // This prevents us from resetting mOldTailoringComboBoxIdx!
                    }

                    mScanningSession->setTailoringFile(filePath);
                    // tailoring has been loaded from a tailoring file, there are no tailoring changes to save
                    markLoadedTailoringFile(filePath);
                    tailoringLoaded = true;
                }
            }
            else if (text == TAILORING_UNSAVED)
            {
                // NOOP
                return; // Avoid reloading the session
            }
            else
            {
                mDiagnosticsDialog->errorMessage(QString(
                    QObject::tr("Can't set scanning session to use customization '%1' (from combobox "
                    "item data). As item QVariant data was QString::Null() "
                    "'%2', '%3' or '%4' was expected as item text.")).arg(text, TAILORING_NONE, TAILORING_CUSTOM_FILE, TAILORING_UNSAVED));
            }
        }
        else
        {
            if (data == mLoadedTailoringFileUserData)
            {
                // User selected the already loaded tailoring file. -> NOOP
                return; // Avoid reloading the session
            }
            else
            {
                mScanningSession->setTailoringComponentID(data.toString());
                tailoringLoaded = true;
            }
        }

        // We intentionally call mScanningSession->reloadSession() instead of MainWindow::reloadSession
        // because we want to catch exceptions and not have these filtered.
        mScanningSession->setSkipValid(mSkipValid);
        mScanningSession->reloadSession();
    }
    catch (const std::exception& e)
    {
        // Something went wrong when setting the tailoring file, lets reset tailoring
        // to the most likely *sane* state to avoid errors when scanning.
        mUI.tailoringFileComboBox->setCurrentIndex(0);
        mDiagnosticsDialog->exceptionMessage(e, QObject::tr("Failed to set up tailoring."));
    }

    reloadSession();
    if (tailoringLoaded)
    {
        const std::map<QString, struct xccdf_profile*> profiles = mScanningSession->getAvailableProfiles();

        // Select the first tailored profile from the newly loaded tailoring
        for (std::map<QString, struct xccdf_profile*>::const_iterator it = profiles.begin();
             it != profiles.end(); ++it)
        {
            if (xccdf_profile_get_tailoring(it->second))
            {
                const QString profileId = it->first;
                const int idx = mUI.profileComboBox->findData(QVariant(profileId));
                if (idx != -1)
                    mUI.profileComboBox->setCurrentIndex(idx);
                break;
            }
        }
    }

    mOldTailoringComboBoxIdx = index;
}

void MainWindow::profileComboboxChanged(int index)
{
    if (mIgnoreProfileComboBox)
        return;

    if (!fileOpened())
        return;

    const QString profileId = mUI.profileComboBox->itemData(index).toString();

    try
    {
        mScanningSession->setProfile(profileId);
        mUI.customizeProfileButton->setEnabled(true);
    }
    catch (std::exception& e)
    {
        // At this point we can't be sure a valid profile is selected.
        // We better disallow tailoring.
        mUI.customizeProfileButton->setEnabled(false);

        mDiagnosticsDialog->exceptionMessage(e, QObject::tr("Failed to select XCCDF profile."));
    }

    mUI.ruleResultsTree->refreshSelectedRules(mScanningSession);
    clearResults();
}

void MainWindow::toggleRuleResultsExpanded()
{
    mRuleResultsExpanded = !mRuleResultsExpanded;

    setRuleResultsExpanded(mRuleResultsExpanded);
}

void MainWindow::toggleRuleResultsExpanded(bool checked)
{
    mRuleResultsExpanded = checked;

    setRuleResultsExpanded(mRuleResultsExpanded);
}

void MainWindow::setRuleResultsExpanded(bool checked)
{
    mUI.ruleResultsTree->toggleAllRuleResultDescription(checked);
    setActionToggleRuleResultsText(checked);

}

void MainWindow::allRuleResultsExpanded(bool checked)
{
    mRuleResultsExpanded = checked;
    setActionToggleRuleResultsText(checked);
}

void MainWindow::setActionToggleRuleResultsText(bool checked)
{
    if(checked)
        mUI.expandRulesButton->setText(QString("Collapse all"));
    else
        mUI.expandRulesButton->setText(QString("Expand all"));
}

void MainWindow::scanProgressReport(const QString& rule_id, const QString& result)
{
    /* It is quite hard to accurately estimate completion of SCAP scans.
       Our method is quite naive and simplistic, we keep filling the
       result tree, we know the amount of selected rules. Our estimation
       is that each rule takes the same amount of time. The percentage of
       completion is "uniqueResults / selectedRuleCount".

       We must only count unique result because multi check causes one rule
       to produce multiple result. This would skew our estimation to be too
       optimistic!
    */

    if (result != "processing")
    {
        // Guard ourselves against multi checks, only count each rule result once
        // for progress estimation.
        if (!mUI.ruleResultsTree->hasRuleResult(rule_id))
            mUI.progressBar->setValue(mUI.progressBar->value() + 1);
    }

    try
    {
        mUI.ruleResultsTree->injectRuleResult(rule_id, result);
    }
    catch (const RuleResultsTreeException& e)
    {
        scanWarningMessage(e.what());
    }
}

void MainWindow::scanInfoMessage(const QString& message)
{
    statusBar()->showMessage(message);
    mDiagnosticsDialog->infoMessage(message);
}

void MainWindow::scanWarningMessage(const QString& message)
{
    mDiagnosticsDialog->warningMessage(message);
}

void MainWindow::scanErrorMessage(const QString &message)
{
    mDiagnosticsDialog->errorMessage(message);
}

void MainWindow::scanCanceled()
{
    scanEnded(true);
}

void MainWindow::scanFinished()
{
    scanEnded(false);

    // Clean results if the scan is a dry run
    // User will see the CommandLineArgsDialog and then the MainWindow
    // ready for a new scan, or dry run
    if (mUI.dryRunCheckBox->isChecked())
        clearResults();
}

void MainWindow::scanEnded(bool canceled)
{
    if (canceled)
    {
        mUI.cancelButton->setEnabled(true);

        // Essentially, this is done to notify the user that the progress results
        // are only partial. Yet it could be useful to review them so we don't
        // clear them completely.
        mUI.ruleResultsTree->setEnabled(false);
    }
    else
    {
        mUI.progressBar->setValue(mUI.progressBar->maximum());
        mUI.resultViewer->loadContent(mScanner);
        mUI.offlineRemediateButton->setEnabled(mScanner->getScannerMode() == SM_SCAN);
    }

    mUI.preScanTools->hide();
    mUI.preScanTools->setEnabled(false);
    mUI.scanTools->hide();
    mUI.scanTools->setEnabled(false);
    mUI.postScanTools->show();
    mUI.postScanTools->setEnabled(true);

    mUI.resultViewer->setEnabled(!canceled);

    mUI.menuSave->setEnabled(true);
    mUI.actionOpen->setEnabled(true);

    cleanupScanThread();
}

void MainWindow::openCustomizationFile()
{
    int idx = mUI.tailoringFileComboBox->findText(TAILORING_CUSTOM_FILE);
    if (idx == -1)
        return;

    mUI.tailoringFileComboBox->setCurrentIndex(idx);
}

void MainWindow::inheritAndEditProfile(bool shadowed)
{
    if (!fileOpened())
        return;

    struct xccdf_profile* newProfile = 0;

    try
    {
        const struct xccdf_version_info* versionInfo = mScanningSession->getXCCDFVersionInfo();
        const QStringList version = QString(xccdf_version_info_get_version(versionInfo)).split(".");
        // are we dealing with XCCDF 1.2 or greater?
        const bool xccdf12 = version[0].toInt() > 1 || (version[0].toInt() == 1 && version[1].toInt() >= 2);

        const QString newIdBase = mScanningSession->getProfile().isEmpty() ?
            "xccdf_scap-workbench_profile_default_customized" : mScanningSession->getProfile() +"_customized";

        TailorProfileDialog dialog(newIdBase, xccdf12, this);
        if (dialog.exec() == QDialog::Rejected)
            return;

        newProfile = mScanningSession->tailorCurrentProfile(shadowed, dialog.getProfileID());
    }
    catch (const std::exception& e)
    {
        mDiagnosticsDialog->exceptionMessage(e, QObject::tr("Failed to customize currently selected profile."));
        return;
    }

    refreshProfiles();

    // select the new profile as current
    int indexCandidate = mUI.profileComboBox->findData(QVariant(QString::fromUtf8(xccdf_profile_get_id(newProfile))));
    if (indexCandidate != -1)
        mUI.profileComboBox->setCurrentIndex(indexCandidate);

    // and edit it
    editProfile(true);
}

TailoringWindow* MainWindow::editProfile(bool newProfile)
{
    if (!fileOpened())
        return 0;

    struct xccdf_session* session = 0;
    struct xccdf_policy* policy = 0;
    try
    {
        session = mScanningSession->getXCCDFSession();
        policy = xccdf_session_get_xccdf_policy(session);
    }
    catch (const std::exception& e)
    {
        mDiagnosticsDialog->exceptionMessage(e, QObject::tr("Failed to retrieve XCCDF policy when editing profile."));
        return 0;
    }

    if (!policy)
        return 0;

    struct xccdf_profile* profile = xccdf_policy_get_profile(policy);
    if (!profile)
        return 0;

    if (!xccdf_profile_get_tailoring(profile))
    {
        mDiagnosticsDialog->errorMessage(QObject::tr(
                "Can't edit a profile that isn't a tailoring profile!"
                "This is most likely a bug, please report it!"
            )
        );

        return 0;
    }

    struct xccdf_policy_model* policyModel = xccdf_session_get_policy_model(session);
    struct xccdf_benchmark* benchmark = xccdf_policy_model_get_benchmark(policyModel);

    TailoringWindow* ret = new TailoringWindow(policy, benchmark, newProfile, this);
    ret->setAttribute(Qt::WA_DeleteOnClose, true);
#ifndef _WIN32
    // disabling MainWindow on Windows causes workbench to hang
    setEnabled(false);
#endif
    return ret;
}

void MainWindow::customizeProfile()
{
    if (!fileOpened())
        return;

    if (mScanningSession->isSelectedProfileTailoring())
        editProfile(false);
    else
        inheritAndEditProfile(false);
}

void MainWindow::saveTailoring()
{
    const QFileInfo openedFile(getOpenedFilePath());

    const QString path = QFileDialog::getSaveFileName(this,
        QObject::tr("Save Customization As"),
        QDir(getDefaultSaveDirectory()).absoluteFilePath(QString("%1-tailoring.xml").arg(openedFile.baseName())),
        QObject::tr("XCCDF Tailoring file (*.xml)"), 0
#ifndef SCAP_WORKBENCH_USE_NATIVE_FILE_DIALOGS
        , QFileDialog::DontUseNativeDialog
#endif
    );

    if (path.isEmpty())
        return;

    notifySaveActionConfirmed(path, false);

    try
    {
        mScanningSession->saveTailoring(path, true);
        markUnsavedTailoringChanges();
        markLoadedTailoringFile(path);
    }
    catch (const std::exception& e)
    {
        // Just to be sure user doesn't lose the tailoring.
        markUnsavedTailoringChanges();
        mDiagnosticsDialog->exceptionMessage(e, QObject::tr("Failed to save tailoring file."));
    }
}

void MainWindow::saveIntoDirectory()
{
    if (!fileOpened())
        return;

    const QString targetPath = QFileDialog::getExistingDirectory(this,
        QObject::tr("Select target directory"),
        getDefaultSaveDirectory(),
        QFileDialog::ShowDirsOnly
#ifndef SCAP_WORKBENCH_USE_NATIVE_FILE_DIALOGS
        | QFileDialog::DontUseNativeDialog
#endif
    );
    if (targetPath.isEmpty())
        return; // user canceled

    notifySaveActionConfirmed(targetPath, true);

    try
    {
        mScanningSession->saveOpenedFilesClosureToDir(targetPath);
    }
    catch (const std::exception& e)
    {
        mDiagnosticsDialog->exceptionMessage(e, QObject::tr("Failed to save opened files."));
    }
}

void MainWindow::saveAsRPM()
{
    if (!fileOpened())
        return;

    SaveAsRPMDialog::saveSession(mScanningSession, this);
}

void MainWindow::markUnsavedTailoringChanges()
{
    int idx = mUI.tailoringFileComboBox->findText(TAILORING_UNSAVED);
    if (idx == -1)
    {
        mUI.tailoringFileComboBox->addItem(QString(TAILORING_UNSAVED), QVariant(QString::Null()));
        idx = mUI.tailoringFileComboBox->findText(TAILORING_UNSAVED);
    }

    mUI.tailoringFileComboBox->setCurrentIndex(idx);

    idx = mUI.tailoringFileComboBox->findData(mLoadedTailoringFileUserData);
    if (idx != -1)
        mUI.tailoringFileComboBox->removeItem(idx);

    mLoadedTailoringFileUserData = TAILORING_NO_LOADED_FILE_DATA;
}

void MainWindow::markNoUnsavedTailoringChanges()
{
    const int idx = mUI.tailoringFileComboBox->findText(TAILORING_UNSAVED);
    if (idx != -1)
        mUI.tailoringFileComboBox->removeItem(idx);
}

void MainWindow::markRemoveLoadedTailoringFile()
{
    const int idx = mUI.tailoringFileComboBox->findData(mLoadedTailoringFileUserData);
    if (idx != -1)
        mUI.tailoringFileComboBox->removeItem(idx);
}

void MainWindow::markLoadedTailoringFile(const QString& filePath)
{
    markRemoveLoadedTailoringFile();

    mLoadedTailoringFileUserData = QVariant(filePath);
    mUI.tailoringFileComboBox->addItem(filePath, mLoadedTailoringFileUserData);
    mUI.tailoringFileComboBox->setCurrentIndex(mUI.tailoringFileComboBox->findData(mLoadedTailoringFileUserData));

    markNoUnsavedTailoringChanges();
}

bool MainWindow::unsavedTailoringChanges() const
{
    if (!fileOpened())
        return false;

    const int idx = mUI.tailoringFileComboBox->findText(TAILORING_UNSAVED);
    return mUI.tailoringFileComboBox->currentIndex() == idx;
}

QString MainWindow::getDefaultSaveDirectory()
{
    return mQSettings->value("last_save_directory", "").toString();
}

void MainWindow::notifySaveActionConfirmed(const QString& path, bool isDir)
{
    const QString absoluteDirPath = isDir ? path : QFileInfo(path).dir().absolutePath();
    mQSettings->setValue("last_save_directory", absoluteDirPath);
}

void MainWindow::showGuide()
{
    if (!fileOpened())
        return;

    openUrlGuarded(QUrl::fromLocalFile(mScanningSession->getGuideFilePath()));
}

void MainWindow::showUserManual()
{
    openUrlGuarded(QUrl::fromLocalFile(getDocDirectory().absoluteFilePath("user_manual.html")));
}

void MainWindow::about()
{
    const QString title = "SCAP Workbench " SCAP_WORKBENCH_VERSION;

    const QString versionInfo = QString("<p>SCAP Workbench %1, compiled with Qt %2, using OpenSCAP %3</p>").arg(SCAP_WORKBENCH_VERSION, QT_VERSION_STR, oscap_get_version());
    const QString description = QObject::tr(
"<p>This application is called SCAP Workbench, the homepage can be found at \
<a href='https://www.open-scap.org/tools/scap-workbench/'>https://www.open-scap.org/tools/scap-workbench/</a></p>");
    const QString license = QString(
"<p>Copyright 2014 Red Hat Inc., Durham, North Carolina.<br/>\
All Rights Reserved.</p>\
\
<p>This program is free software: you can redistribute it and/or modify \
it under the terms of the GNU General Public License as published by \
the Free Software Foundation, either version 3 of the License, or \
(at your option) any later version.</p>\
\
<p>This program is distributed in the hope that it will be useful, \
but WITHOUT ANY WARRANTY; without even the implied warranty of \
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the \
GNU General Public License for more details.</p>\
\
<p>You should have received a copy of the GNU General Public License \
along with this program.  If not, see <a href='http://www.gnu.org/licenses/'>http://www.gnu.org/licenses/</a>.</p>");

    QMessageBox::about(this, title, versionInfo + description + license);
}

void MainWindow::aboutQt()
{
    QMessageBox::aboutQt(this);
}

QMessageBox::StandardButton MainWindow::openNewFileQuestionDialog(const QString& oldFilepath)
{
    return QMessageBox::question(this,
          QObject::tr("Close currently opened file?"),
          QObject::tr("Opened file '%1' has to be closed before opening another file.\n\n"
          "Do you want to proceed?").arg(oldFilepath),
          QMessageBox::Yes | QMessageBox::No, QMessageBox::No
    );
}
