#include "MainWindow.h"

#include <QFileDialog>
#include <QMessageBox>

#include <cassert>

extern "C" {
#include <xccdf_policy.h>
#include <xccdf_session.h>
#include <scap_ds.h>
#include <oscap_error.h>
}

MainWindow::MainWindow(QWidget* parent):
    QMainWindow(parent),

    mSession(0)
{
    mUI.setupUi(this);

    QObject::connect(
        mUI.fileCloseButton, SIGNAL(released()),
        this, SLOT(openFileDialog())
    );

    QObject::connect(
        mUI.checklistComboBox, SIGNAL(currentIndexChanged(const QString&)),
        this, SLOT(checklistComboboxChanged(const QString&))
    );

    show();

    openFileDialog();
}

MainWindow::~MainWindow()
{
    closeFile();
}

void MainWindow::clearResults()
{
    mUI.preScanTools->show();
    mUI.postScanTools->hide();

    mUI.ruleResultsTree->clear();
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
        QMessageBox::critical(this, QString("Failed to create session for '%1'").arg(path),
            QString("OpenSCAP error message:\n%1").arg(oscap_err_desc()));
        return;
    }

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
                mUI.checklistComboBox->addItem(QString("%1 / %2").arg(stream_id).arg(checklist_id));
            }
            oscap_string_iterator_free(checklists_it);
        }
        ds_stream_index_iterator_free(streams_it);

        mUI.checklistComboBox->show();
        mUI.checklistLabel->show();
    }

    // force load up of the session
    checklistComboboxChanged("");
    setEnabled(true);
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

    mUI.profileComboBox->clear();

    clearResults();
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
            QApplication::instance()->quit();
            // TODO: ^^^ this doesn't work properly!
            return;
        }

        openFile(path);
    }
}

void MainWindow::reloadSession()
{
    if (!mSession)
        return;

    if (xccdf_session_load(mSession) != 0)
    {
        QMessageBox::critical(this, QString("Failed to reload session"),
            QString("OpenSCAP error message:\n%1").arg(oscap_err_desc()));
    }

    refreshProfiles();
}

void MainWindow::refreshProfiles()
{
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

    // TODO: we likely want profile titles shown in the future, not their IDs
    struct xccdf_tailoring* tailoring = xccdf_policy_model_get_tailoring(pmodel);
    if (tailoring)
    {
        profile_it = xccdf_tailoring_get_profiles(tailoring);
        while (xccdf_profile_iterator_has_more(profile_it))
        {
            struct xccdf_profile* profile = xccdf_profile_iterator_next(profile_it);
            const QString profile_id = QString(xccdf_profile_get_id(profile));

            assert(profileCrossMap.find(profile_id) == profileCrossMap.end());

            profileCrossMap.insert(
                std::make_pair(
                    profile_id,
                    profile_id
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
                    profile_id
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
}

void MainWindow::checklistComboboxChanged(const QString& text)
{
    if (!mSession)
        return;

    const QStringList split = text.split(" / ");

    if (split.size() == 2)
    {
        xccdf_session_set_datastream_id(mSession, split.at(0).toUtf8().constData());
        xccdf_session_set_component_id(mSession, split.at(1).toUtf8().constData());
    }
    else
    {
        xccdf_session_set_datastream_id(mSession, 0);
        xccdf_session_set_component_id(mSession, 0);
    }

    reloadSession();
}
