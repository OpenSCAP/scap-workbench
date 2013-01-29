#include "MainWindow.h"

#include <QFileDialog>
#include <QMessageBox>

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
