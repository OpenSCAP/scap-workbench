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

    mSession(0),

    mScanThread(0),
    mScanner(0),

    mResultViewer(0),
    mDiagnosticsDialog(0)
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

    mResultViewer = new ResultViewer(this);
    mResultViewer->hide();

    mDiagnosticsDialog = new DiagnosticsDialog(this);
    mDiagnosticsDialog->hide();

    show();
}

MainWindow::~MainWindow()
{
    closeFile();
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
    if (mSession)
    {
        closeFile();
    }

    mSession = xccdf_session_new(path.toUtf8().constData());
    if (!mSession)
    {
        mDiagnosticsDialog->errorMessage(
            QString("Failed to create session for '%1'. OpenSCAP error message:\n%2").arg(path).arg(oscap_err_desc()));
        return;
    }

    mUI.tailoringFileComboBox->addItem(QString("(none)"), QVariant(QString::Null()));

    mUI.openedFileLineEdit->setText(path);
    if (xccdf_session_is_sds(mSession))
    {
        struct ds_sds_index* sds_idx = xccdf_session_get_sds_idx(mSession);

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
    setEnabled(true);
}

void MainWindow::openFileDialog()
{
    closeFile();

    while (!mSession)
    {
        QString path = QFileDialog::getOpenFileName(this,
            "Open Source DataStream or XCCDF file",
            "/home/mpreisle/d/openscap/dist/", // TODO: temporary
            "Source DataStream, XCCDF or tailoring file (*.xml)"
        );

        if (path == QString::Null())
        {
            // user cancelled the dialog, exit the entire app gracefully
            close();
            return;
        }

        openFile(path);
        if (!mSession)
        {
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

void MainWindow::scanAsync(bool onlineRemediation)
{
    assert(mSession);
    assert(!mScanner);
    assert(!mScanThread);

    clearResults();

    mUI.scanProperties->setEnabled(false);
    mUI.preScanTools->hide();
    mUI.scanTools->show();

    struct xccdf_policy* policy = xccdf_session_get_xccdf_policy(mSession);
    if (!policy)
    {
        mDiagnosticsDialog->errorMessage(
            QString("Can't get XCCDF policy from the session. Very likely it failed to load. OpenSCAP error message:\n%1").arg(oscap_err_desc()));

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

    if (target == "localhost")
        mScanner = new OscapScannerLocal(mScanThread);
    else
        mScanner = new OscapScannerRemoteSsh(mScanThread);

    mScanner->setSession(mSession);
    mScanner->setTarget(target);
    mScanner->setOnlineRemediationEnabled(onlineRemediation);

    mScanner->moveToThread(mScanThread);

    QObject::connect(
        mScanThread, SIGNAL(started()),
        mScanner, SLOT(evaluate())
    );
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

    mScanThread->start();
}

void MainWindow::scanAndRemediateAsync()
{
    scanAsync(true);
}

void MainWindow::cancelScanAsync()
{
    assert(mSession);

    mUI.cancelButton->setEnabled(false);
    emit cancelScan();
}

void MainWindow::closeFile()
{
    if (mSession)
    {
        xccdf_session_free(mSession);
        mSession = 0;
    }

    setEnabled(false);

    mUI.openedFileLineEdit->setText("");

    mUI.checklistComboBox->clear();
    mUI.checklistComboBox->hide();
    mUI.checklistLabel->hide();

    mUI.tailoringFileComboBox->clear();

    mUI.profileComboBox->clear();

    clearResults();
    mDiagnosticsDialog->clear();
}

void MainWindow::reloadSession()
{
    if (!mSession)
        return;

    clearResults();

    if (xccdf_session_load(mSession) != 0)
    {
        mDiagnosticsDialog->errorMessage(
            QString("Failed to reload session. OpenSCAP error message:\n%1").arg(oscap_err_desc()));
        return;
    }

    refreshProfiles();
}

void MainWindow::refreshProfiles()
{
    const int previousIndex = mUI.profileComboBox->currentIndex();
    const QString previouslySelected = previousIndex == -1 ?
        QString::Null() : mUI.profileComboBox->itemData(previousIndex).toString();

    mUI.profileComboBox->clear();

    if (!mSession)
        return;

    mUI.profileComboBox->addItem("(default)", QVariant(QString::Null()));

    struct xccdf_policy_model* pmodel = xccdf_session_get_policy_model(mSession);

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

            assert(profileCrossMap.find(profile_id) == profileCrossMap.end());

            profileCrossMap.insert(
                std::make_pair(
                    profile_id,
                    oscap_textlist_get_preferred_plaintext(titles, NULL)
                )
            );
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
                    oscap_textlist_get_preferred_plaintext(titles, NULL)
                )
            );
        }
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

void MainWindow::cleanupScanThread()
{
    mScanThread->deleteLater();
    delete mScanner;

    mScanThread = 0;
    mScanner = 0;

    mUI.progressBar->setRange(0, 1);
    mUI.progressBar->reset();
    mUI.progressBar->setEnabled(false);
}

void MainWindow::checklistComboboxChanged(int index)
{
    if (!mSession)
        return;

    const QStringList data = mUI.checklistComboBox->itemData(index).toStringList();

    if (data.size() == 2)
    {
        xccdf_session_set_datastream_id(mSession, data.at(0).toUtf8().constData());
        xccdf_session_set_component_id(mSession, data.at(1).toUtf8().constData());
    }
    else
    {
        xccdf_session_set_datastream_id(mSession, 0);
        xccdf_session_set_component_id(mSession, 0);
    }

    reloadSession();
}

void MainWindow::tailoringFileComboboxChanged(int index)
{
    if (!mSession)
        return;

    const QString text = mUI.tailoringFileComboBox->itemText(index);
    const QString data = mUI.tailoringFileComboBox->itemData(index).toString();

    if (data == QString::Null()) // special cases first
    {
        if (text == TAILORING_NONE)
        {
            xccdf_session_set_user_tailoring_file(mSession, NULL);
            xccdf_session_set_user_tailoring_cid(mSession, NULL);
        }
        else if (text == TAILORING_CUSTOM_FILE)
        {
            QString filePath = QFileDialog::getOpenFileName(
                this, "Open custom XCCDF tailoring file", QString(),
                "XCCDF tailoring file (*.xml)"
            );

            if (filePath == QString::Null())
            {
                // user canceled, set to (none)
                mUI.tailoringFileComboBox->setCurrentIndex(0);
            }
            else
            {
                xccdf_session_set_user_tailoring_cid(mSession, NULL);
                xccdf_session_set_user_tailoring_file(mSession, filePath.toUtf8().constData());
            }
        }
        else
        {
            // TODO: report something meaningful
            assert(0);
        }
    }
    else
    {
        xccdf_session_set_user_tailoring_file(mSession, NULL);
        xccdf_session_set_user_tailoring_cid(mSession, data.toUtf8().constData());
    }

    reloadSession();
}

void MainWindow::profileComboboxChanged(int index)
{
    if (!mSession)
        return;

    QString profileId = mUI.profileComboBox->itemData(index).toString();

    if (profileId == QString::Null())
    {
        xccdf_session_set_profile_id(mSession, 0);
    }
    else
    {
        if (!xccdf_session_set_profile_id(mSession, profileId.toUtf8().constData()))
        {
            xccdf_session_set_profile_id(mSession, 0);

            mDiagnosticsDialog->warningMessage(
                QString(
                    "Can't change session profile to '%1'!\n"
                    "oscap error description:\n%2"
                ).arg(profileId).arg(oscap_err_desc())
            );
        }
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

    assert(mSession);

    struct xccdf_benchmark* benchmark = xccdf_policy_model_get_benchmark(xccdf_session_get_policy_model(mSession));
    struct xccdf_item* item = xccdf_benchmark_get_member(benchmark, XCCDF_ITEM, rule_id.toUtf8().constData());

    if (!item)
    {
        scanWarningMessage(QString("Received scanning progress of rule of ID '%1'. "
                                   "Rule with such ID hasn't been found in the benchmark!").arg(rule_id));
        return;
    }

    // Guard ourselves against multi checks, only count each rule result once
    // for progress estimation.
    if (mUI.ruleResultsTree->findItems(rule_id, Qt::MatchExactly, 0).empty())
        mUI.progressBar->setValue(mUI.progressBar->value() + 1);

    QStringList resultRow;
    resultRow.append(oscap_textlist_get_preferred_plaintext(xccdf_item_get_title(item), NULL));
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

    cleanupScanThread();

    mUI.preScanTools->hide();
    mUI.scanTools->hide();
    mUI.postScanTools->show();

    statusBar()->clearMessage();
}

void MainWindow::showResults()
{
    mResultViewer->show();
}
