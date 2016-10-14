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

#include "ResultViewer.h"
#include "Scanner.h"
#include "ScanningSession.h"
#include "Utils.h"

#include <QFileDialog>
#include <QMessageBox>

ResultViewer::ResultViewer(QWidget* parent):
    QWidget(parent),

    mReportFile(0)
{
    mUI.setupUi(this);

    mSaveResultsAction = new QAction("&XCCDF Result file", this);
    QObject::connect(
        mSaveResultsAction, SIGNAL(triggered()),
        this, SLOT(saveResults())
    );
    mSaveARFAction = new QAction("&ARF", this);
    QObject::connect(
        mSaveARFAction, SIGNAL(triggered()),
        this, SLOT(saveARF())
    );
    mSaveReportAction = new QAction("&HTML Report", this);
    QObject::connect(
        mSaveReportAction, SIGNAL(triggered()),
        this, SLOT(saveReport())
    );
    mSaveMenu = new QMenu(this);
    mSaveMenu->addAction(mSaveResultsAction);
    mSaveMenu->addAction(mSaveARFAction);
    mSaveMenu->addAction(mSaveReportAction);
    mUI.saveButton->setMenu(mSaveMenu);

    QObject::connect(
        mUI.openReportButton, SIGNAL(clicked()),
        this, SLOT(openReport())
    );
}

ResultViewer::~ResultViewer()
{
    delete mReportFile;
    mReportFile = 0;
}

void ResultViewer::clear()
{
    mInputBaseName.clear();

    mResults.clear();
    mReport.clear();
    mARF.clear();
}

void ResultViewer::loadContent(Scanner* scanner)
{
    mInputBaseName = "scap";

    ScanningSession* session = scanner->getSession();
    if (session)
    {
        QFileInfo openedFile(session->getOpenedFilePath());
        mInputBaseName = openedFile.baseName();

        if (mInputBaseName.endsWith("-xccdf"))
            mInputBaseName.chop(QString("-xccdf").length());
    }

    mReport.clear();
    scanner->getReport(mReport);

    mResults.clear();
    scanner->getResults(mResults);

    mARF.clear();
    scanner->getARF(mARF);
}

const QByteArray& ResultViewer::getARF() const
{
    return mARF;
}

void ResultViewer::saveReport()
{
    const QString filename = QFileDialog::getSaveFileName(this,
        QObject::tr("Save Report (HTML)"),
        QObject::tr("%1-xccdf.report.html").arg(mInputBaseName),
        QObject::tr("HTML Report (*.html)"), 0
#ifndef SCAP_WORKBENCH_USE_NATIVE_FILE_DIALOGS
        , QFileDialog::DontUseNativeDialog
#endif
    );

    if (filename.isEmpty())
        return;

    QFile file(filename);
    file.open(QIODevice::WriteOnly);
    file.write(mReport);
    file.close();
}

void ResultViewer::openReport()
{
    if (mReportFile)
    {
        delete mReportFile;
        mReportFile = 0;
    }

    mReportFile = new QTemporaryFile();
    mReportFile->setFileTemplate(mReportFile->fileTemplate() + ".html");
    mReportFile->open();
    mReportFile->write(mReport);
    mReportFile->flush();
    mReportFile->close();

    openUrlGuarded(QUrl::fromLocalFile(mReportFile->fileName()));

    // the temporary file will be destroyed when SCAP Workbench closes or after another one is requested
}

void ResultViewer::saveResults()
{
    const QString filename = QFileDialog::getSaveFileName(this,
        QObject::tr("Save as XCCDF Results"),
        QObject::tr("%1-xccdf.results.xml").arg(mInputBaseName),
        QObject::tr("XCCDF Results (*.xml)"), 0
#ifndef SCAP_WORKBENCH_USE_NATIVE_FILE_DIALOGS
        , QFileDialog::DontUseNativeDialog
#endif
    );

    if (filename.isEmpty())
        return;

    QFile file(filename);
    file.open(QIODevice::WriteOnly);
    file.write(mResults);
    file.close();
}

void ResultViewer::saveARF()
{
    const QString filename = QFileDialog::getSaveFileName(this,
        QObject::tr("Save as Result DataStream / ARF"),
        QObject::tr("%1-arf.xml").arg(mInputBaseName),
        QObject::tr("Result DataStream / ARF (*.xml)"), 0
#ifndef SCAP_WORKBENCH_USE_NATIVE_FILE_DIALOGS
        , QFileDialog::DontUseNativeDialog
#endif
    );

    if (filename.isEmpty())
        return;

    QFile file(filename);
    file.open(QIODevice::WriteOnly);
    file.write(mARF);
    file.close();
}
