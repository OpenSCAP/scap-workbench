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
#include "TailoringWindow.h"
#include "ScanningSession.h"
#include "Exceptions.h"
#include "APIHelpers.h"
#include "SaveAsRPMDialog.h"

#include <QFileDialog>
#include <QAbstractEventDispatcher>
#include <QMessageBox>
#include <QCloseEvent>

#include <cassert>
#include <set>

extern "C" {
#include <xccdf_policy.h>
#include <xccdf_session.h>
#include <scap_ds.h>
}

// A dialog to open a tailoring file is displayed after user selects this option
// from the tailoring combobox.
const QString TAILORING_CUSTOM_FILE = "(open tailoring file...)";
// This option signifies that there is no tailoring being done and the plain
// content file is used, it also resets tailoring when selected.
const QString TAILORING_NONE = "(no tailoring)";
// Signifies that tailoring changes have been made and have not been saved
// to a file (yet?). Selecting it does nothing.
const QString TAILORING_UNSAVED = "(unsaved changes)";

// Magic string that we use to distinguish that we have no loaded tailoring file
// in the tailoring combobox.
const QVariant TAILORING_NO_LOADED_FILE_DATA = "&*&()@#$(no loaded file)";

MainWindow::MainWindow(QWidget* parent):
    QMainWindow(parent),

    mDiagnosticsDialog(0),

    mScanningSession(0),

    mScanThread(0),
    mScanner(0),

    mOldTailoringComboBoxIdx(0),
    mLoadedTailoringFileUserData(TAILORING_NO_LOADED_FILE_DATA)
{
    mUI.setupUi(this);
    mUI.progressBar->reset();

    // we start with localhost which doesn't need remote machine details
    mUI.remoteMachineDetails->hide();

    QObject::connect(
        this, SIGNAL(showOpenFileDialog()),
        this, SLOT(openFileDialog()),
        // Queued to prevent opening a blocking dialog before event loop is
        // entered. Without this the application wouldn't quit gracefully.
        Qt::QueuedConnection
    );
    QObject::connect(
        mUI.openButton, SIGNAL(released()),
        this, SLOT(openFileDialog())
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
    QObject::connect(
        mUI.scanButton, SIGNAL(released()),
        this, SLOT(scanAsyncAutoMode())
    );
    QObject::connect(
        mUI.offlineRemediateButton, SIGNAL(released()),
        this, SLOT(offlineRemediateAsync())
    );
    QObject::connect(
        mUI.cancelButton, SIGNAL(released()),
        this, SLOT(cancelScanAsync())
    );
    QObject::connect(
        mUI.clearButton, SIGNAL(released()),
        this, SLOT(clearResults())
    );
    QObject::connect(
        mUI.showResultsButton, SIGNAL(released()),
        this, SLOT(showResults())
    );

    mSaveIntoDirAction = new QAction("Save into a directory", this);
    QObject::connect(
        mSaveIntoDirAction, SIGNAL(triggered()),
        this, SLOT(saveIntoDirectory())
    );
    mSaveAsRPMAction = new QAction("Save as RPM", this);
    QObject::connect(
        mSaveAsRPMAction, SIGNAL(triggered()),
        this, SLOT(saveAsRPM())
    );
    mSaveMenu = new QMenu(this);
    mSaveMenu->addAction(mSaveIntoDirAction);
    mSaveMenu->addAction(mSaveAsRPMAction);
    mUI.saveButton->setMenu(mSaveMenu);

    QObject::connect(
        mUI.customizeProfileButton, SIGNAL(released()),
        this, SLOT(customizeProfile())
    );

    QObject::connect(
        mUI.saveTailoringButton, SIGNAL(released()),
        this, SLOT(saveTailoring())
    );

    mUI.selectedRulesTree->show();
    mUI.selectedRulesTree->header()->setResizeMode(0, QHeaderView::Stretch);
    mUI.ruleResultsTree->hide();
    mUI.ruleResultsTree->header()->setResizeMode(0, QHeaderView::Stretch);

    // FIXME: This is hidden to avoid people trying to use it when it is still
    //        not supported in openscap.
    mUI.offlineRemediateButton->hide();

#if (QT_VERSION >= QT_VERSION_CHECK(4, 7, 0))
    // placeholder text is only supported in Qt 4.7 onwards
    mUI.remoteMachineHost->setPlaceholderText("username@hostname");
#endif

    mResultViewer = new ResultViewer(this);
    mResultViewer->hide();

    mDiagnosticsDialog = new DiagnosticsDialog(this);
    mDiagnosticsDialog->hide();

    mScanningSession = new ScanningSession();

    closeFile();
    show();
}

MainWindow::~MainWindow()
{
    delete mScanner;
    mScanner = 0;

    closeFile();
    delete mScanningSession;

    delete mResultViewer;
}

void MainWindow::clearResults()
{
    mUI.scanProperties->setEnabled(true);

    mUI.preScanTools->show();
    mUI.preScanTools->setEnabled(true);
    mUI.scanTools->hide();
    mUI.scanTools->setEnabled(false);
    mUI.postScanTools->hide();
    mUI.postScanTools->setEnabled(false);

    mUI.ruleResultsTree->clear();
    mUI.ruleResultsTree->setEnabled(false);

    mResultViewer->clear();

    mUI.selectedRulesTree->show();
    mUI.ruleResultsTree->hide();
}

void MainWindow::openFile(const QString& path)
{
    try
    {
        mScanningSession->openFile(path);

        const QFileInfo pathInfo(path);
        setWindowTitle(QString("%1 - scap-workbench").arg(pathInfo.fileName()));

        mUI.tailoringFileComboBox->addItem(QString(TAILORING_NONE), QVariant(QString::Null()));
        mUI.tailoringFileComboBox->addItem(QString(TAILORING_CUSTOM_FILE), QVariant(QString::Null()));
        // we have just loaded the input file fresh, there are no tailoring changes to save
        markNoUnsavedTailoringChanges();

        refreshChecklists();
        // force load up of the session
        checklistComboboxChanged(0);

        centralWidget()->setEnabled(true);

        mDiagnosticsDialog->infoMessage(QString("Opened file '%1'.").arg(path));
    }
    catch (const std::exception& e)
    {
        mScanningSession->closeFile();

        setWindowTitle("scap-workbench");
        mUI.tailoringFileComboBox->clear();

        mDiagnosticsDialog->exceptionMessage(e, "Error while opening file.");
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
            "Open Source DataStream or XCCDF file",
            defaultDirectory,
            "Source DataStream, XCCDF or tailoring file (*.xml);;All files (*)"
        );

        if (path == QString::Null())
            // user cancelled the dialog, get out of this loop
            break;

        if (fileOpened())
        {
            if (QMessageBox::question(this, "Close currently opened file?",
                QString("Opened file has to be closed before '%1' is opened instead.\n\n"
                        "Are you sure you want to close currently opened file?").arg(path),
                QMessageBox::Yes | QMessageBox::No, QMessageBox::No) == QMessageBox::Yes)
            {
                closeFile();
            }
            else
                // user cancelled closing current file, we have to abort
                break;
        }

        openFile(path);

        if (!fileOpened())
        {
            // Error occured, keep pumping events and don't move on until user
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

void MainWindow::openFileDialogAsync()
{
    emit showOpenFileDialog();
}

bool MainWindow::fileOpened() const
{
    return mScanningSession && mScanningSession->fileOpened();
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

    mUI.scanProperties->setEnabled(false);
    mUI.preScanTools->hide();
    mUI.preScanTools->setEnabled(false);
    mUI.scanTools->show();
    mUI.scanTools->setEnabled(true);

    mUI.selectedRulesTree->hide();
    mUI.ruleResultsTree->show();

    struct xccdf_policy* policy = xccdf_session_get_xccdf_policy(mScanningSession->getXCCDFSession());
    if (!policy)
    {
        mDiagnosticsDialog->errorMessage(QString(
            "Can't get XCCDF policy from the session. Very likely it failed to load. "
            "OpenSCAP error message:\n%1").arg(oscapErrDesc()));

        mUI.scanProperties->setEnabled(true);
        mUI.preScanTools->show();
        mUI.preScanTools->setEnabled(true);
        mUI.scanTools->hide();
        mUI.scanTools->setEnabled(false);

        return;
    }

    mUI.progressBar->setRange(0, xccdf_policy_get_selected_rules_count(policy));
    mUI.progressBar->reset();
    mUI.progressBar->setEnabled(true);
    mUI.ruleResultsTree->setEnabled(true);

    mScanThread = new QThread(this);

    // We pack the port to the end of target solely for the ease of comparing
    // targets (which can avoid reconnection and reauthentication).
    // In the OscapScannerRemoteSsh class the port will be parsed out again...
    const QString target = mUI.localMachineRadioButton->isChecked() ?
        "localhost" : QString("%1:%2").arg(mUI.remoteMachineHost->text()).arg(mUI.remoteMachinePort->value());

    try
    {
        if (!mScanner || mScanner->getTarget() != target)
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
                mScanner, SIGNAL(progressReport(const QString&, const QString&)),
                this, SLOT(scanProgressReport(const QString&, const QString&))
            );
            QObject::connect(
                mScanner, SIGNAL(infoMessage(const QString&)),
                this, SLOT(scanInfoMessage(const QString&))
            );
            QObject::connect(
                mScanner, SIGNAL(warningMessage(const QString&)),
                this, SLOT(scanWarningMessage(const QString&))
            );
            QObject::connect(
                mScanner, SIGNAL(errorMessage(const QString&)),
                this, SLOT(scanErrorMessage(const QString&))
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
        mScanner->setSession(mScanningSession);
        mScanner->setScannerMode(scannerMode);

        if (scannerMode == SM_OFFLINE_REMEDIATION)
        {
            // TODO: Allow user to tweak the results to deselect/select rules to remediate, etc...
            mScanner->setARFForRemediation(mResultViewer->getARF());
        }
    }
    catch (const std::exception& e)
    {
        scanCanceled();
        mDiagnosticsDialog->exceptionMessage(e, "There was a problem setting up the scanner.");
        return;
    }

    mScanner->moveToThread(mScanThread);

    QObject::connect(
        mScanThread, SIGNAL(started()),
        mScanner, SLOT(evaluateExceptionGuard())
    );

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

void MainWindow::closeEvent(QCloseEvent* event)
{
    if (mScanThread)
    {
        if (QMessageBox::question(this, "Cancel scan in progress?",
            "A scan is in progress. Are you sure you want to terminate it and close the application?",
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
        if (QMessageBox::question(this, "Unsaved tailoring changes",
            "There are unsaved tailoring changes, closing scap-workbench will destroy them. "
            "Are you sure you want to close and discard the changes?",
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

    mDiagnosticsDialog->infoMessage("Closing the main window...");
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

        mDiagnosticsDialog->exceptionMessage(e, "Failed to close file.");
    }

    centralWidget()->setEnabled(false);

    setWindowTitle("scap-workbench");

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

    mResultViewer->clear();
    mUI.titleLabel->setText(mScanningSession->getBenchmarkTitle());
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
    refreshSelectedRulesTree();
}

void MainWindow::refreshProfiles()
{
    const int previousIndex = mUI.profileComboBox->currentIndex();
    const QString previouslySelected = previousIndex == -1 ?
        QString::Null() : mUI.profileComboBox->itemData(previousIndex).toString();

    mUI.profileComboBox->clear();

    if (!fileOpened())
        return;

    try
    {
        const std::map<QString, struct xccdf_profile*> profiles = mScanningSession->getAvailableProfiles();

        // A nice side effect here is that profiles will be sorted by their IDs
        // because of the RB-tree implementation of std::map.
        for (std::map<QString, struct xccdf_profile*>::const_iterator it = profiles.begin();
             it != profiles.end(); ++it)
        {
            const QString profileTitle = oscapTextIteratorGetPreferred(xccdf_profile_get_title(it->second));
            mUI.profileComboBox->addItem(profileTitle, QVariant(it->first));
        }

        if (previouslySelected != QString::Null())
        {
            const int indexCandidate = mUI.profileComboBox->findData(QVariant(previouslySelected));
            if (indexCandidate != -1)
                mUI.profileComboBox->setCurrentIndex(indexCandidate);
        }

        // Intentionally comes last. Users are more likely to use profiles other than (default)
#if (QT_VERSION >= QT_VERSION_CHECK(4, 4, 0))
        mUI.profileComboBox->insertSeparator(mUI.profileComboBox->count());
#endif
        mUI.profileComboBox->addItem("(default)", QVariant(QString::Null()));
    }
    catch (const std::exception& e)
    {
        mUI.profileComboBox->clear();
        mDiagnosticsDialog->exceptionMessage(e, "Error while refreshing available XCCDF profiles.");
    }
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

            mUI.checklistComboBox->show();
            mUI.checklistLabel->show();
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
    mScanThread->wait();
    mScanThread->deleteLater();
    mScanThread = 0;

    mUI.progressBar->setRange(0, 1);
    mUI.progressBar->reset();
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

    try
    {
        if (data.toString() == QString::Null()) // Null data means it's an action
        {
            if (text == TAILORING_NONE) // resets tailoring
            {
                if (mUI.saveTailoringButton->isEnabled())
                {
                    if (QMessageBox::question(this, "Unsaved tailoring changes!",
                            "Are you sure you want to reset tailoring and wipe all unsaved tailoring changes?",
                            QMessageBox::Yes | QMessageBox::No, QMessageBox::No) == QMessageBox::No)
                    {
                        mUI.tailoringFileComboBox->setCurrentIndex(mOldTailoringComboBoxIdx); // user canceled, set to previous value
                        return; // This prevents us from resetting mOldTailoringComboBoxIdx!
                    }
                }

                mScanningSession->resetTailoring();
                // tailoring has been reset, there are no tailoring changes to save
                markNoUnsavedTailoringChanges();
            }
            else if (text == TAILORING_CUSTOM_FILE) // loads custom file
            {
                const QString filePath = QFileDialog::getOpenFileName(
                    this, "Open custom XCCDF tailoring file", QString(),
                    "XCCDF tailoring file (*.xml)"
                );

                if (filePath == QString::Null())
                {
                    mUI.tailoringFileComboBox->setCurrentIndex(mOldTailoringComboBoxIdx); // user canceled, set to previous value
                    return; // This prevents us from resetting mOldTailoringComboBoxIdx!
                }
                else
                {
                    if (mScanningSession->hasTailoring() &&
                        QMessageBox::question(this, "Unsaved tailoring changes!",
                            "Are you sure you want to load a tailoring file and wipe all unsaved tailoring changes?",
                            QMessageBox::Yes | QMessageBox::No, QMessageBox::No) == QMessageBox::No)
                    {
                        mUI.tailoringFileComboBox->setCurrentIndex(mOldTailoringComboBoxIdx); // user canceled, set to previous value
                        return; // This prevents us from resetting mOldTailoringComboBoxIdx!
                    }

                    mScanningSession->setTailoringFile(filePath);
                    // tailoring has been loaded from a tailoring file, there are no tailoring changes to save
                    markLoadedTailoringFile(filePath);
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
                    "Can't set scanning session to use tailoring '%1' (from combobox "
                    "item data). As item QVariant data was QString::Null() "
                    "'%2', '%3' or '%4' was expected as item text.").arg(text, TAILORING_NONE, TAILORING_CUSTOM_FILE, TAILORING_UNSAVED));
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
            }
        }

        // We intentionally call mScanningSession->reloadSession() instead of MainWindow::reloadSession
        // because we want to catch exceptions and not have these filtered.
        mScanningSession->reloadSession();
    }
    catch (const std::exception& e)
    {
        // Something went wrong when setting the tailoring file, lets reset tailoring
        // to the most likely *sane* state to avoid errors when scanning.
        mUI.tailoringFileComboBox->setCurrentIndex(0);
        mDiagnosticsDialog->exceptionMessage(e, "Failed to set up tailoring.");
    }

    reloadSession();

    mOldTailoringComboBoxIdx = index;
}

void MainWindow::profileComboboxChanged(int index)
{
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

        mDiagnosticsDialog->exceptionMessage(e, "Failed to select XCCDF profile.");
    }

    refreshSelectedRulesTree();
    clearResults();
}

/*
Unfortunately, xccdf_policy won't let us see its "selected-final" hashmap.
Instead we have to gather all rules and for each rule ID we check the policy.
*/
inline void gatherAllSelectedRules(struct xccdf_policy* policy, struct xccdf_item* current,
    std::vector<struct xccdf_rule*>& result)
{
    if (xccdf_item_get_type(current) == XCCDF_RULE)
    {
        struct xccdf_rule* rule = xccdf_item_to_rule(current);
        const bool selected = xccdf_policy_is_item_selected(policy, xccdf_rule_get_id(rule));

        if (selected)
            result.push_back(rule);
    }
    else if (xccdf_item_get_type(current) == XCCDF_BENCHMARK ||
        xccdf_item_get_type(current) == XCCDF_GROUP)
    {
        struct xccdf_item_iterator* it = xccdf_item_get_content(current);
        while (xccdf_item_iterator_has_more(it))
        {
            struct xccdf_item* item = xccdf_item_iterator_next(it);
            gatherAllSelectedRules(policy, item, result);
        }
        xccdf_item_iterator_free(it);
    }
}

void MainWindow::refreshSelectedRulesTree()
{
    mUI.selectedRulesTree->clear();

    if (!fileOpened())
        return;

    struct xccdf_session* session = mScanningSession->getXCCDFSession();
    struct xccdf_policy* policy = xccdf_session_get_xccdf_policy(session);
    struct xccdf_select_iterator* sel_it = xccdf_policy_get_selected_rules(policy);

    struct xccdf_benchmark* benchmark = 0;
    try
    {
        benchmark = xccdf_policy_model_get_benchmark(xccdf_session_get_policy_model(mScanningSession->getXCCDFSession()));
    }
    catch (const std::exception& e)
    {
        // This is not a critical error, just quit
        // FIXME: We should display some sort of an error indicator though to get bug reports!
        return;
    }

    std::vector<struct xccdf_rule*> selectedRules;

    gatherAllSelectedRules(policy, xccdf_benchmark_to_item(benchmark), selectedRules);

    mUI.selectedRulesTree->setUpdatesEnabled(false);

    // we filter through a set to avoid duplicates and get a sensible ordering
    for (std::vector<struct xccdf_rule*>::const_iterator it = selectedRules.begin();
         it != selectedRules.end(); ++it)
    {
        struct xccdf_rule* rule = *it;
        const QString preferredTitle = oscapTextIteratorGetPreferred(xccdf_rule_get_title(rule));
        const QString preferredDesc = oscapTextIteratorGetPreferred(xccdf_rule_get_description(rule));

        QTreeWidgetItem* treeItem = new QTreeWidgetItem();
        treeItem->setText(0, preferredTitle);
        treeItem->setToolTip(0, preferredDesc);

        mUI.selectedRulesTree->addTopLevelItem(treeItem);
    }

    mUI.selectedRulesTree->setUpdatesEnabled(true);

    xccdf_select_iterator_free(sel_it);
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

    assert(fileOpened());

    struct xccdf_benchmark* benchmark = 0;
    try
    {
        benchmark = xccdf_policy_model_get_benchmark(xccdf_session_get_policy_model(mScanningSession->getXCCDFSession()));
    }
    catch (const std::exception& e)
    {
        scanErrorMessage(QString("Can't get benchmark from scanning session, details follow:\n%1").arg(QString::fromUtf8(e.what())));

        return;
    }

    struct xccdf_item* item = xccdf_benchmark_get_member(benchmark, XCCDF_ITEM, rule_id.toUtf8().constData());

    if (!item)
    {
        scanWarningMessage(QString(
            "Received scanning progress of rule of ID '%1'. "
            "Rule with such ID hasn't been found in the benchmark!").arg(rule_id));

        return;
    }

    // Guard ourselves against multi checks, only count each rule result once
    // for progress estimation.
    if (mUI.ruleResultsTree->findItems(rule_id, Qt::MatchExactly, 0).empty())
        mUI.progressBar->setValue(mUI.progressBar->value() + 1);

    const QString preferredTitle = oscapTextIteratorGetPreferred(xccdf_item_get_title(item));
    const QString preferredDesc = oscapTextIteratorGetPreferred(xccdf_item_get_description(item));

    QBrush resultBrush;
    if (result == "processing")
        resultBrush.setColor(Qt::darkYellow);
    else if (result == "pass")
        resultBrush.setColor(Qt::darkGreen);
    else if (result == "fixed")
        resultBrush.setColor(Qt::darkGreen);
    else if (result == "fail")
        resultBrush.setColor(Qt::red);
    else if (result == "error")
        resultBrush.setColor(Qt::red);
    else
        resultBrush.setColor(Qt::darkGray);

    QTreeWidgetItem* treeItem = 0;

    QTreeWidgetItem* replacementCandidate = mUI.ruleResultsTree->topLevelItemCount() > 0 ? mUI.ruleResultsTree->topLevelItem(mUI.ruleResultsTree->topLevelItemCount() - 1) : 0;
    if (replacementCandidate && replacementCandidate->text(0) == preferredTitle && replacementCandidate->text(1) == "processing")
        treeItem = replacementCandidate;

    if (!treeItem)
        treeItem = new QTreeWidgetItem();

    treeItem->setText(0, preferredTitle);
    treeItem->setToolTip(0, preferredDesc);
    treeItem->setText(1, result);

    treeItem->setForeground(1, resultBrush);

    // Highlight currently processed rule
    QBrush backgroundBrush(Qt::NoBrush);
    if (result == "processing")
        backgroundBrush = QBrush(Qt::lightGray);
    treeItem->setBackground(0, backgroundBrush);
    treeItem->setBackground(1, backgroundBrush);

    if (treeItem != replacementCandidate)
    {
        // TODO: This is causing a redraw and is a massive slowdown
        //       Ideally we would group all items that we want added
        //       and add them at once, causing only one redraw.
        mUI.ruleResultsTree->addTopLevelItem(treeItem);
    }

    // ensure the updated item is visible
    mUI.ruleResultsTree->scrollToItem(treeItem);
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
        mResultViewer->loadContent(mScanner);
        mUI.offlineRemediateButton->setEnabled(mScanner->getScannerMode() == SM_SCAN);
    }

    mUI.preScanTools->hide();
    mUI.preScanTools->setEnabled(false);
    mUI.scanTools->hide();
    mUI.scanTools->setEnabled(false);
    mUI.postScanTools->show();
    mUI.postScanTools->setEnabled(true);

    mUI.showResultsButton->setEnabled(!canceled);

    cleanupScanThread();
    statusBar()->clearMessage();
}

void MainWindow::showResults()
{
    mResultViewer->show();
}

void MainWindow::inheritAndEditProfile(bool shadowed)
{
    if (!fileOpened())
        return;

    struct xccdf_profile* newProfile = 0;

    try
    {
        newProfile = mScanningSession->tailorCurrentProfile(shadowed);
    }
    catch (const std::exception& e)
    {
        mDiagnosticsDialog->exceptionMessage(e, "Failed to tailor currently selected profile.");
    }

    refreshProfiles();

    // select the new profile as current
    int indexCandidate = mUI.profileComboBox->findData(QVariant(QString::fromUtf8(xccdf_profile_get_id(newProfile))));
    if (indexCandidate != -1)
        mUI.profileComboBox->setCurrentIndex(indexCandidate);

    // and edit it
    editProfile(true);
}

void MainWindow::editProfile(bool newProfile)
{
    if (!fileOpened())
        return;

    struct xccdf_session* session = 0;
    struct xccdf_policy* policy = 0;
    try
    {
        session = mScanningSession->getXCCDFSession();
        policy = xccdf_session_get_xccdf_policy(session);
    }
    catch (const std::exception& e)
    {
        mDiagnosticsDialog->exceptionMessage(e, "Failed to retrieve XCCDF policy when editing profile.");
        return;
    }

    if (!policy)
        return;

    struct xccdf_profile* profile = xccdf_policy_get_profile(policy);
    if (!profile)
        return;

    if (!xccdf_profile_get_tailoring(profile))
    {
        mDiagnosticsDialog->errorMessage(
            QString(
                "Can't edit a profile that isn't a tailoring profile!"
                "This is most likely a bug, please report it!"
            )
        );

        return;
    }

    struct xccdf_policy_model* policyModel = xccdf_session_get_policy_model(session);
    struct xccdf_benchmark* benchmark = xccdf_policy_model_get_benchmark(policyModel);

    new TailoringWindow(policy, benchmark, newProfile, this);
    // The tailoring that is going to be done is not part of anything saved on disk.
    // User might want to save it
    markUnsavedTailoringChanges();
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
    const QString path = QFileDialog::getSaveFileName(this, "Save Tailoring As", "", "XCCDF Tailoring file (*.xml)");

    if (path.isEmpty())
        return;

    try
    {
        mScanningSession->saveTailoring(path);
        markLoadedTailoringFile(path);
    }
    catch (const std::exception& e)
    {
        // Just to be sure user doesn't lose the tailoring.
        markUnsavedTailoringChanges();
        mDiagnosticsDialog->exceptionMessage(e, "Failed to save tailoring file.");
    }
}

void MainWindow::saveIntoDirectory()
{
    if (!fileOpened())
        return;

    const QString targetPath = QFileDialog::getExistingDirectory(this, "Select target directory");
    if (targetPath.isEmpty())
        return; // user canceled

    try
    {
        mScanningSession->saveOpenedFilesClosureToDir(targetPath);
    }
    catch (const std::exception& e)
    {
        mDiagnosticsDialog->exceptionMessage(e, "Failed to save opened files.");
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
    mUI.saveTailoringButton->setEnabled(true);

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
    mUI.saveTailoringButton->setEnabled(false);

    const int idx = mUI.tailoringFileComboBox->findText(TAILORING_UNSAVED);
    if (idx != -1)
        mUI.tailoringFileComboBox->removeItem(idx);
}

void MainWindow::markLoadedTailoringFile(const QString& filePath)
{
    const int idx = mUI.tailoringFileComboBox->findData(mLoadedTailoringFileUserData);
    if (idx != -1)
        mUI.tailoringFileComboBox->removeItem(idx);

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
