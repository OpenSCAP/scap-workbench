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

#include <QFileDialog>
#include <QDesktopServices>
#include <QMessageBox>
#ifdef SCAP_WORKBENCH_USE_WEBKIT
#   include <QWebFrame>
#endif

ResultViewer::ResultViewer(QWidget* parent):
    QWidget(parent)
{
    mUI.setupUi(this);

    mSaveResultsAction = new QAction("XCCDF Result file", this);
    QObject::connect(
        mSaveResultsAction, SIGNAL(triggered()),
        this, SLOT(saveResults())
    );
    mSaveARFAction = new QAction("ARF", this);
    QObject::connect(
        mSaveARFAction, SIGNAL(triggered()),
        this, SLOT(saveARF())
    );
    mSaveReportAction = new QAction("HTML Report", this);
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
        mUI.openReportButton, SIGNAL(released()),
        this, SLOT(openReport())
    );
}

ResultViewer::~ResultViewer()
{}

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
    const QString filename = QFileDialog::getSaveFileName(this, "Save Report (HTML)", QString("%1-xccdf.report.html").arg(mInputBaseName), "HTML Report (*.html)");

    if (filename == QString::Null())
        return;

    QFile file(filename);
    file.open(QIODevice::WriteOnly);
    file.write(mReport);
    file.close();
}

void ResultViewer::openReport()
{
    mReportFile.open();
    mReportFile.write(mReport);
    mReportFile.flush();

    QDesktopServices::openUrl(QUrl::fromLocalFile(mReportFile.fileName()));

    mReportFile.close();

    // the temporary file will be destroyed when scap-workbench closes
}

void ResultViewer::saveResults()
{
    const QString filename = QFileDialog::getSaveFileName(this, "Save as XCCDF Results", QString("%1-xccdf.results.xml").arg(mInputBaseName), "XCCDF Results (*.xml)");

    if (filename == QString::Null())
        return;

    QFile file(filename);
    file.open(QIODevice::WriteOnly);
    file.write(mResults);
    file.close();
}

void ResultViewer::saveARF()
{
    const QString filename = QFileDialog::getSaveFileName(this, "Save as Result DataStream / ARF", QString("%1-arf.xml").arg(mInputBaseName), "Result DataStream / ARF (*.xml)");

    if (filename == QString::Null())
        return;

    QFile file(filename);
    file.open(QIODevice::WriteOnly);
    file.write(mARF);
    file.close();
}
