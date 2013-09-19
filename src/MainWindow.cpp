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

#include <QFileDialog>
#include <QAbstractEventDispatcher>

#include <cassert>

extern "C" {
#include <xccdf_policy.h>
#include <xccdf_session.h>
#include <scap_ds.h>
#include <oscap_error.h>
}

const QString TAILORING_CUSTOM_FILE = "(...)";
const QString TAILORING_NONE = "(none)";

MainWindow::MainWindow(QWidget* parent):
    QMainWindow(parent),

    mDiagnosticsDialog(0),

    mScanningSession(0),

    mScanThread(0),
    mScanner(0)
{
    mUI.setupUi(this);
    mUI.progressBar->reset();

    // Target has to be in the [USER@]HOSTNAME[:PORT] scheme.
    QString targetRegExp = "^([a-z][-a-z0-9]*@)?"; // username, optional
    // [1] http://perldoc.net/Regexp/Common/URI/RFC2396.pm
    // [2] https://www.ietf.org/rfc/rfc2396.txt
    targetRegExp += "(?:(?:(?:(?:[a-zA-Z0-9][-a-zA-Z0-9]*)?[a-zA-Z0-9])[.])*(?:[a-zA-Z][-a-zA-Z0-9]*[a-zA-Z0-9]|[a-zA-Z])[.]?)"; // hostname, required
    targetRegExp += "(:[0-9]+)?"; // port, optional
    mUI.targetLineEdit->setValidator(new QRegExpValidator(QRegExp(targetRegExp), this));

    QObject::connect(
        this, SIGNAL(showOpenFileDialog()),
        this, SLOT(openFileDialog()),
        // Queued to prevent opening a blocking dialog before event loop is
        // entered. Without this the application wouldn't quit gracefully.
        Qt::QueuedConnection
    );
    QObject::connect(
        mUI.fileCloseButton, SIGNAL(released()),
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
        this, SLOT(scanAsync())
    );
    QObject::connect(
        mUI.scanAndRemediateButton, SIGNAL(released()),
        this, SLOT(scanAndRemediateAsync())
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

    mTailorAction = new QAction("Tailor (new ID)", this);
    QObject::connect(
        mTailorAction, SIGNAL(triggered()),
        this, SLOT(tailorNewID())
    );
    mTailorAndShadowAction = new QAction("Tailor (shadowed = same ID)", this);
    QObject::connect(
        mTailorAndShadowAction, SIGNAL(triggered()),
        this, SLOT(tailorShadowed())
    );
    mEditProfileAction = new QAction("Edit profile", this);
    QObject::connect(
        mEditProfileAction, SIGNAL(triggered()),
        this, SLOT(editProfile())
    );

    mTailorButtonMenu = new QMenu(this);
    mTailorButtonMenu->addAction(mTailorAction);
    mTailorButtonMenu->addAction(mTailorAndShadowAction);
    mTailorButtonMenu->addAction(mEditProfileAction);
    mUI.tailorButton->setMenu(mTailorButtonMenu);

    QObject::connect(
        mUI.saveTailoringButton, SIGNAL(released()),
        this, SLOT(saveTailoring())
    );

    mResultViewer = new ResultViewer(this);
    mResultViewer->hide();

    mDiagnosticsDialog = new DiagnosticsDialog(this);
    mDiagnosticsDialog->hide();

    mScanningSession = new ScanningSession();

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
    mUI.scanTools->hide();
    mUI.postScanTools->hide();

    mUI.ruleResultsTree->clear();
    mUI.ruleResultsTree->setEnabled(false);

    mResultViewer->clear();
}

void MainWindow::openFile(const QString& path)
{
    try
    {
        mScanningSession->openFile(path);

        mUI.tailoringFileComboBox->addItem(QString("(none)"), QVariant(QString::Null()));

        mUI.openedFileLineEdit->setText(path);
        if (mScanningSession->isSDS())
        {
            struct ds_sds_index* sds_idx = xccdf_session_get_sds_idx(mScanningSession->getXCCDFSession());

            struct ds_stream_index_iterator* streams_it = ds_sds_index_get_streams(sds_idx);
            while (ds_stream_index_iterator_has_more(streams_it))
            {
                struct ds_stream_index* stream_idx = ds_stream_index_iterator_next(streams_it);
                const char* stream_id = ds_stream_index_get_id(stream_idx);

                struct oscap_string_iterator* checklists_it = ds_stream_index_get_checklists(stream_idx);
                while (oscap_string_iterator_has_more(checklists_it))
                {
                    const char* checklist_id = oscap_string_iterator_next(checklists_it);

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

            // TODO: Tailoring files inside datastream should be added to tailoring combobox
        }

        mUI.tailoringFileComboBox->addItem(QString("(...)"), QVariant(QString::Null()));

        // force load up of the session
        checklistComboboxChanged(0);

        centralWidget()->setEnabled(true);

        mDiagnosticsDialog->infoMessage(QString("Opened file '%1'.").arg(path));
    }
    catch (const std::exception& e)
    {
        mScanningSession->closeFile();

        mUI.tailoringFileComboBox->clear();
        mUI.openedFileLineEdit->setText("");
        mUI.checklistComboBox->clear();

        mDiagnosticsDialog->errorMessage(e.what());
    }
}

void MainWindow::openFileDialog()
{
    closeFile();

    while (!mScanningSession->fileOpened())
    {
        QString path = QFileDialog::getOpenFileName(this,
            "Open Source DataStream or XCCDF file",
            "",
            "Source DataStream, XCCDF or tailoring file (*.xml);;All files (*)",
            0,
            QFileDialog::DontUseNativeDialog
        );

        if (path == QString::Null())
        {
            // user cancelled the dialog, exit the entire app gracefully
            if (!close())
                throw MainWindowException("Failed to close main window!");

            return;
        }

        openFile(path);

        if (!mScanningSession->fileOpened())
        {
            // Error occured, keep pumping events and don't move on until user
            // dismisses diagnostics dialog.
            while (mDiagnosticsDialog->isVisible())
            {
                QAbstractEventDispatcher::instance(0)->processEvents(QEventLoop::AllEvents);
            }
        }
    }
}

void MainWindow::openFileDialogAsync()
{
    emit showOpenFileDialog();
}

void MainWindow::scanAsync(ScannerMode scannerMode)
{
    assert(mScanningSession->fileOpened());
    assert(!mScanThread);

    clearResults();

    mUI.scanProperties->setEnabled(false);
    mUI.preScanTools->hide();
    mUI.scanTools->show();

    struct xccdf_policy* policy = xccdf_session_get_xccdf_policy(mScanningSession->getXCCDFSession());
    if (!policy)
    {
        mDiagnosticsDialog->errorMessage(QString(
            "Can't get XCCDF policy from the session. Very likely it failed to load. "
            "OpenSCAP error message:\n%1").arg(oscap_err_desc()));

        mUI.scanProperties->setEnabled(true);
        mUI.preScanTools->show();
        mUI.scanTools->hide();

        return;
    }

    mUI.progressBar->setRange(0, xccdf_policy_get_selected_rules_count(policy));
    mUI.progressBar->reset();
    mUI.progressBar->setEnabled(true);
    mUI.ruleResultsTree->setEnabled(true);

    mScanThread = new QThread(this);

    const QString target = mUI.targetLineEdit->text();

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

    try
    {
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
        mDiagnosticsDialog->errorMessage(
            QString("There was a problem when setting up the scanner. Details follow:\n%1").arg(e.what()));

        scanCanceled();
        return;
    }

    mScanner->moveToThread(mScanThread);

    QObject::connect(
        mScanThread, SIGNAL(started()),
        mScanner, SLOT(evaluate())
    );

    mScanThread->start();
}

void MainWindow::scanAndRemediateAsync()
{
    scanAsync(SM_SCAN_ONLINE_REMEDIATION);
}

void MainWindow::offlineRemediateAsync()
{
    scanAsync(SM_OFFLINE_REMEDIATION);
}

void MainWindow::cancelScanAsync()
{
    assert(mScanningSession->fileOpened());

    mUI.cancelButton->setEnabled(false);
    emit cancelScan();
}

void MainWindow::closeEvent(QCloseEvent* event)
{
    if (mScanningSession->fileOpened())
        cancelScanAsync();

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
        mDiagnosticsDialog->errorMessage(e.what());
    }

    centralWidget()->setEnabled(false);

    mUI.openedFileLineEdit->setText("");

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
        mDiagnosticsDialog->errorMessage(e.what());
    }

    mResultViewer->clear();
    refreshProfiles();
}

void MainWindow::refreshProfiles()
{
    const int previousIndex = mUI.profileComboBox->currentIndex();
    const QString previouslySelected = previousIndex == -1 ?
        QString::Null() : mUI.profileComboBox->itemData(previousIndex).toString();

    mUI.profileComboBox->clear();

    if (!mScanningSession->fileOpened())
        return;

    mUI.profileComboBox->addItem("(default)", QVariant(QString::Null()));

    try
    {
        struct xccdf_policy_model* pmodel = xccdf_session_get_policy_model(mScanningSession->getXCCDFSession());

        // We construct a temporary map that maps profile IDs to what we will show
        // in the combobox. We do this to convey that some profiles are shadowed
        // (tailored) in the tailoring file.

        std::map<QString, QString> profileCrossMap;
        struct xccdf_profile_iterator* profile_it;

        struct xccdf_tailoring* tailoring = xccdf_policy_model_get_tailoring(pmodel);
        if (tailoring)
        {
            profile_it = xccdf_tailoring_get_profiles(tailoring);
            while (xccdf_profile_iterator_has_more(profile_it))
            {
                struct xccdf_profile* profile = xccdf_profile_iterator_next(profile_it);
                const QString profile_id = QString(xccdf_profile_get_id(profile));
                oscap_text_iterator* titles = xccdf_profile_get_title(profile);
                char* preferred_title = oscap_textlist_get_preferred_plaintext(titles, NULL);
                oscap_text_iterator_free(titles);

                assert(profileCrossMap.find(profile_id) == profileCrossMap.end());

                profileCrossMap.insert(
                    std::make_pair(
                        profile_id,
                        QString(preferred_title)
                    )
                );

                free(preferred_title);
            }
            xccdf_profile_iterator_free(profile_it);
        }

        struct xccdf_benchmark* benchmark = xccdf_policy_model_get_benchmark(pmodel);
        profile_it = xccdf_benchmark_get_profiles(benchmark);
        while (xccdf_profile_iterator_has_more(profile_it))
        {
            struct xccdf_profile* profile = xccdf_profile_iterator_next(profile_it);
            const QString profile_id = QString(xccdf_profile_get_id(profile));
            oscap_text_iterator* titles = xccdf_profile_get_title(profile);
            char* preferred_title = oscap_textlist_get_preferred_plaintext(titles, NULL);
            oscap_text_iterator_free(titles);

            if (profileCrossMap.find(profile_id) != profileCrossMap.end())
            {
                // this profile is being shadowed by the tailoring file
                profileCrossMap[profile_id] += " (tailored)";
            }
            else
            {
                profileCrossMap.insert(
                    std::make_pair(
                        profile_id,
                        QString(preferred_title)
                    )
                );
            }

            free(preferred_title);
        }
        xccdf_profile_iterator_free(profile_it);

        // A nice side effect here is that profiles will be sorted by their IDs
        // because of the RB-tree implementation of std::map. I am not sure whether
        // we want that in the final version but it works well for the content
        // I am testing with.
        for (std::map<QString, QString>::const_iterator it = profileCrossMap.begin();
             it != profileCrossMap.end();
             ++it)
        {
            mUI.profileComboBox->addItem(it->second, QVariant(it->first));
        }

        if (previouslySelected != QString::Null())
        {
            int indexCandidate = mUI.profileComboBox->findData(QVariant(previouslySelected));
            if (indexCandidate != -1)
                mUI.profileComboBox->setCurrentIndex(indexCandidate);
        }
    }
    catch (const std::exception& e)
    {
        mUI.profileComboBox->clear();
        mDiagnosticsDialog->errorMessage(e.what());
    }
}

void MainWindow::cleanupScanThread()
{
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
        mDiagnosticsDialog->errorMessage(e.what());
    }
}

void MainWindow::tailoringFileComboboxChanged(int index)
{
    if (!mScanningSession->fileOpened())
        return;

    const QString text = mUI.tailoringFileComboBox->itemText(index);
    const QString data = mUI.tailoringFileComboBox->itemData(index).toString();

    try
    {
        if (data == QString::Null()) // special cases first
        {
            if (text == TAILORING_NONE)
            {
                mScanningSession->resetTailoring();
            }
            else if (text == TAILORING_CUSTOM_FILE)
            {
                QString filePath = QFileDialog::getOpenFileName(
                    this, "Open custom XCCDF tailoring file", QString(),
                    "XCCDF tailoring file (*.xml)"
                );

                if (filePath == QString::Null())
                    mUI.tailoringFileComboBox->setCurrentIndex(0); // user canceled, set to (none)
                else
                    mScanningSession->setTailoringFile(filePath);
            }
            else
            {
                mDiagnosticsDialog->errorMessage(QString(
                    "Can't set scanning session to use tailoring '%1' (from combobox "
                    "item data). Expected '%2' or '%3'").arg(text).arg(TAILORING_NONE).arg(TAILORING_CUSTOM_FILE));
            }
        }
        else
        {
            mScanningSession->setTailoringComponentID(data);
        }

        reloadSession();
    }
    catch (const std::exception& e)
    {
        mDiagnosticsDialog->errorMessage(e.what());
    }
}

void MainWindow::profileComboboxChanged(int index)
{
    if (!mScanningSession->fileOpened())
        return;

    const QString profileId = mUI.profileComboBox->itemData(index).toString();

    try
    {
        mScanningSession->setProfileID(profileId);

        // scap-workbench can tailor any profile but it doesn't make sense to "tailor" a tailoring profile.
        // Doing so would create yet another profile inheriting the old. Instead we allow user to
        // edit the already tailored profile.

        // Note: We can inherit and edit (default) profile by creating a new empty profile.

        mTailorAction->setEnabled(!mScanningSession->isSelectedProfileTailoring());
        // NB: default profile can't be shadow tailored, it makes no sense
        mTailorAndShadowAction->setEnabled(!profileId.isEmpty() && !mScanningSession->isSelectedProfileTailoring());
        mEditProfileAction->setEnabled(mScanningSession->isSelectedProfileTailoring());
    }
    catch (std::exception& e)
    {
        mDiagnosticsDialog->errorMessage(e.what());

        // At this point we can't be sure a valid profile is selected. We better disallow tailoring.
        mTailorAction->setEnabled(false);
        mTailorAndShadowAction->setEnabled(false);
        mEditProfileAction->setEnabled(false);
    }

    clearResults();
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

    assert(mScanningSession->fileOpened());

    struct xccdf_benchmark* benchmark = 0;
    try
    {
        benchmark = xccdf_policy_model_get_benchmark(xccdf_session_get_policy_model(mScanningSession->getXCCDFSession()));
    }
    catch (const std::exception& e)
    {
        scanErrorMessage(QString("Can't get benchmark from scanning session, details follow:\n%1").arg(e.what()));

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

    QStringList resultRow;
    struct oscap_text_iterator* title_it = xccdf_item_get_title(item);
    char* preferred_title = oscap_textlist_get_preferred_plaintext(title_it, NULL);
    oscap_text_iterator_free(title_it);
    resultRow.append(preferred_title);
    free(preferred_title);
    resultRow.append(result);

    QBrush resultBrush;
    if (result == "pass")
        resultBrush.setColor(Qt::darkGreen);
    else if (result == "fixed")
        resultBrush.setColor(Qt::darkGreen);
    else if (result == "fail")
        resultBrush.setColor(Qt::red);
    else if (result == "error")
        resultBrush.setColor(Qt::red);
    else
        resultBrush.setColor(Qt::darkGray);

    QTreeWidgetItem* treeItem = new QTreeWidgetItem(resultRow);
    treeItem->setForeground(1, resultBrush);
    mUI.ruleResultsTree->addTopLevelItem(treeItem);
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
    mUI.cancelButton->setEnabled(true);

    cleanupScanThread();
    // Essentially, this is done to notify the user that the progress results
    // are only partial. Yet it could be useful to review them so we don't
    // clear them completely.
    mUI.ruleResultsTree->setEnabled(false);

    mUI.scanProperties->setEnabled(true);
    mUI.preScanTools->show();
    mUI.scanTools->hide();
    mUI.postScanTools->hide();

    statusBar()->clearMessage();
}

void MainWindow::scanFinished()
{
    mResultViewer->loadContent(mScanner);

    mUI.preScanTools->hide();
    mUI.scanTools->hide();
    mUI.postScanTools->show();

    mUI.offlineRemediateButton->setEnabled(mScanner->getScannerMode() == SM_SCAN);

    cleanupScanThread();

    statusBar()->clearMessage();
}

void MainWindow::showResults()
{
    mResultViewer->show();
}

void MainWindow::inheritAndEditProfile(bool shadowed)
{
    if (!mScanningSession->fileOpened())
        return;

    struct xccdf_profile* newProfile = 0;

    try
    {
        newProfile = mScanningSession->tailorCurrentProfile(shadowed);
    }
    catch (const std::exception& e)
    {
        mDiagnosticsDialog->errorMessage(
            QString("Failed to tailor currently selected profile, details follow:\n%1").arg(e.what()));
    }

    refreshProfiles();

    // select the new profile as current
    int indexCandidate = mUI.profileComboBox->findData(QVariant(xccdf_profile_get_id(newProfile)));
    if (indexCandidate != -1)
        mUI.profileComboBox->setCurrentIndex(indexCandidate);

    // and edit it
    editProfile();
}

void MainWindow::tailorNewID()
{
    // TODO: Use lambdas
    inheritAndEditProfile(false);
}

void MainWindow::tailorShadowed()
{
    // TODO: Use lambdas
    inheritAndEditProfile(true);
}

void MainWindow::editProfile()
{
    if (!mScanningSession->fileOpened())
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
        mDiagnosticsDialog->errorMessage(
            QString("Failed to retrieve XCCDF policy when editing profile, details follow:%1").arg(e.what()));
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

    new TailoringWindow(policy, benchmark, this);
}

void MainWindow::saveTailoring()
{
    const QString path = QFileDialog::getSaveFileName(this, "Save Tailoring As", "", "XCCDF Tailoring file (*.xml)");

    if (path.isEmpty())
        return;

    try
    {
        mScanningSession->saveTailoring(path);
    }
    catch (const std::exception& e)
    {
        mDiagnosticsDialog->errorMessage(
            QString(
                "Failed to save tailoring file to path '%1'!"
            ).arg(path)
        );
    }
}
